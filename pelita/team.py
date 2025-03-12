
import logging
import os
import subprocess
import sys
import traceback
from io import StringIO
from pathlib import Path
from random import Random
import typing
from urllib.parse import urlparse

import networkx as nx
import zmq

from . import layout
from .base_utils import default_zmq_context
from .layout import BOT_I2N, layout_as_str, wall_dimensions
from .network import PELITA_PORT, RemotePlayerConnection, RemotePlayerRecvTimeout, RemotePlayerSendError

_logger = logging.getLogger(__name__)


def _ensure_list_tuples(list):
    """ Ensures that an iterable is a list of position tuples. """
    return [tuple(item) for item in list]

def _ensure_tuple_tuples(set):
    """ Ensures that an iterable is a tuple of position tuples. """
    return tuple(sorted(tuple(item) for item in set))


def create_homezones(shape, walls):
    width, height = shape
    return [
        tuple((x, y) for x in range(0, width // 2)
                     for y in range(0, height) if (x, y) not in walls),
        tuple((x, y) for x in range(width // 2, width)
                     for y in range(0, height) if (x, y) not in walls)
    ]

def walls_to_graph(walls, shape=None):
    """Return a networkx Graph object given the walls of a maze.

    Parameters
    ----------
    walls : [(x0,y0), (x1,y1), ...]
        a list of wall coordinates
    shape : (int, int)
        the shape of the maze

    Returns
    -------
    graph : networkx.Graph
         a networkx Graph representing the free squares in the maze and their
         connections. Note that 'free' in this context means that the corresponding
         square in the maze is not a wall (but can contain food or bots).

    Notes
    -----
    Nodes in the graph are (x,y) coordinates representing squares in the maze
    which are not walls.
    Edges in the graph are ((x1,y1), (x2,y2)) tuples of coordinates of two
    adjacent squares. Adjacent means that you can go from one square to one of
    its adjacent squares by making one single step (up, down, left, or right).
    """
    graph = nx.Graph()
    if shape is not None:
        width, height = shape
    else:
        width, height = wall_dimensions(walls)

    # ensure that the walls are in a set for faster searches
    walls = set(walls)

    for x in range(width):
        for y in range(height):
            if (x, y) not in walls:
                # this is a free position, get its neighbors
                # Only positive neighbours are needed as we are iterating
                # all fields
                for delta_x, delta_y in [(1, 0), (0, 1)]:
                    neighbor = (x + delta_x, y + delta_y)
                    # we don't need to check for getting neighbors out of the maze
                    # because our mazes are all surrounded by walls, i.e. our
                    # deltas will not put us out of the maze
                    if neighbor not in walls:
                        # this is a genuine neighbor, add an edge in the graph
                        graph.add_edge((x, y), neighbor)
    return graph


def sanitize_say(string):
    """Make input string sane (for a certain definition of sane)"""
    sane = []
    # first of all, verify that the whole thing is valid unicode
    # this should always be True, but who knows where do they get
    # their strings from
    try:
        string.encode('utf8')
    except UnicodeEncodeError:
        raise ValueError(f'{string} is not valid Unicode')
    for c in string:
        if c.isspace():
            # convert newlines and other whitespace to blanks
            char = ' '
        elif int(c.encode('utf8').hex(), 16) <= int("ffff", 16):
            # the character must belong to the Unicode Base Multilingual Plane
            # we get rid of most bullshit with this
            # thanks to Joseph Hale:
            # https://jhale.dev/posts/detecting-basic-multilingual-plane/
            char = c
        else:
            # ignore anything else
            continue
        sane.append(char)
        if len(sane) == 30:
            # break out of the loop when we have 30 chars
            break

    return ''.join(sane)


class Team:
    """
    Wraps a move function and forwards it the `set_initial`
    and `get_move` requests.

    The Team class holds the team’s state between turns, the team’s
    random number generator and the bot track (resets every time a bot
    is killed). This class is also caching bot attributes that do not
    change during the game. Currently cached attributes:
        - bot.walls
        - bot.shape
        - bot._initial_position
        - bot.homezone
        - bot.graph

    Parameters
    ----------
    team_move : function with (bot, state) -> position
        the team’s move function
    team_name :
        the name of the team (optional)

    Raises
    ------
    TypeError : Move is not a function or team_name is not a string
    """
    def __init__(self, team_move: typing.Callable[[typing.Any, typing.Any], typing.Tuple[int, int]], *, team_name=""):
        if not callable(team_move):
            raise TypeError("move is not a function")

        if not isinstance(team_name, str):
            raise TypeError("TEAM_NAME is not a string")

        self._team_move = team_move
        self.team_name = team_name

        #: Storage for the team state
        self._state = {}

        #: The team’s random number generator
        self._rng = None

        #: The history of bot positions
        self._bot_track = [[], []]


    def set_initial(self, team_id, game_state):
        """ Sets the bot indices for the team and returns the team name.
        Currently, we do not call _set_initial on the user side.

        Parameters
        ----------
        team_id : int
            The id of the team
        game_state : dict
            The initial game state
        """
        # Reset the team state
        self._state.clear()

        # Initialize the random number generator
        # with the seed that we received from game
        self._rng = Random(game_state['seed'])

        # Reset the bot tracks
        self._bot_track = [[], []]

        # Store the walls, which are only transmitted once
        self._walls = _ensure_tuple_tuples(game_state['walls'])

        # Store the shape, which is only transmitted once
        self._shape = tuple(game_state['shape'])

        # Cache the initial positions so that we don’t have to calculate them at each step
        self._initial_positions = layout.initial_positions(self._walls, self._shape)

        # Cache the homezone so that we don’t have to create it at each step
        self._homezone = create_homezones(self._shape, self._walls)

        # Cache the graph representation of the maze -> stores a read-only view of the
        # graph, so that local modifications in the move function are not carried
        # over
        self._graph = walls_to_graph(self._walls, shape=self._shape).copy(as_view=True)

    # TODO: get_move could also take the main game state???
    def get_move(self, game_state):
        """ Requests a move from the Player who controls the Bot with id `bot_id`.

        This method returns a dict with a key `move` and a value specifying the direction
        in a tuple. Additionally, a key `say` can be added with a textual value.

        Parameters
        ----------
        game_state : dict
            The initial game state

        Returns
        -------
        move : dict
        """

        me = make_bots(game_state,
                       walls=self._walls,
                       shape=self._shape,
                       initial_positions=self._initial_positions,
                       homezone=self._homezone,
                       rng=self._rng,
                       graph=self._graph)

        team = me._team

        for idx, mybot in enumerate(team):
            # If a bot has been killed, we reset its bot track
            if mybot.was_killed:
                self._bot_track[idx] = []

        # Add our track
        if len(self._bot_track[me._bot_turn]) == 0:
            self._bot_track[me._bot_turn] = [me.position]

        for idx, mybot in enumerate(team):
            # If the track of any bot is empty,
            # add its current position
            if me._bot_turn != idx:
                self._bot_track[idx].append(mybot.position)

            mybot.track = self._bot_track[idx][:]

        move = self.apply_move_fn(self._team_move, team[me._bot_turn], self._state)
        if "error" not in move:
            move["say"] = me._say
        return move

    @staticmethod
    def apply_move_fn(move_fn, bot: "Bot", state):
        try:
            # request a move from the current bot
            move = move_fn(bot, state)
        except Exception as e:
            # Our client had an exception. We print a traceback and
            # return the type of the exception to the server.
            # If this is a remote player, then this will be detected in pelita_player
            # and pelita_player will close the connection automatically.

            # Stacktrace is not needed, when we raise the ValueError above!
            # from rich.console import Console
            # console = Console()

            # if bot.is_blue:
            #     console.print(f"Team [blue]{bot.team_name}[/] caused an exception:")
            # else:
            #     console.print(f"Team [red]{bot.team_name}[/] caused an exception:")

            # console.print_exception(show_locals=True) #, suppress=["pelita"])

            try:
                import _colorize
                colorize = _colorize.can_colorize()
                # This probably only works from Python 3.13 onwards
                traceback.print_exception(sys.exception(), limit=None, file=None, chain=True, colorize=colorize)
            except (ImportError, AttributeError):
                traceback.print_exc()

            return {
                "error": type(e).__name__,
                "error_msg": str(e),
            }

        # check that the returned value is a position tuple
        try:
            if len(move) == 2:
                return { "move": move }

        except TypeError:
            pass

        error = {
            "error": "ValueError",
            "error_msg": f"Function move did not return a valid position: got '{move}' instead."
        }

        from rich.console import Console
        console = Console()
        console.print(f"[b][red]{error['error']}[/red][/b]: {error['error_msg']}")

        # If move cannot take len, we get a type error; convert it to a ValueError
        return error



    def _exit(self, game_state=None):
        """ Dummy function. Only needed for `RemoteTeam`. """
        pass

    def __repr__(self):
        return f'Team({self._team_move!r}, {self.team_name!r})'

## TODO:
# Team -> Team

# Split class RemoteTeam in two:
# One class for handling connections to a server-run Pelita client
# One class that starts its own subprocess and owns it
#
# In the first case, a connection is started with a zmq message
# The game code (setup_teams) is then responsible for awaiting
# the success message
#
# In the second case, the remote client needs to send a success message
# after it has started. The game code (setup_teams) is responsible for awaiting this message
#
# With the Ok message that the process has started, the team name should be included.
#
# The set initial req–rep should be made separately. This ensures that set initial includes the team names
# and the team names do not need to be send during regular move requests.
#
# Rename set_initial -> start_game
#

class RemoteTeam:
    def __init__(self, team_spec, socket):
        self.team_spec = team_spec
        self._team_name = None

        #: Default timeout for a request, unless specified in the game_state
        self.request_timeout = 3

        self.conn = RemotePlayerConnection(socket)

    @property
    def team_name(self):
        return self._team_name

    def wait_ready(self, timeout):
        msg = self.conn.recv_status(timeout)
        try:
            self._team_name = msg['team_name']
        except TypeError:
            raise RemotePlayerRecvTimeout("", "") from None

    def set_initial(self, team_id, game_state):
        timeout_length = game_state['timeout_length']

        msg_id = self.conn.send_req("set_initial", {"team_id": team_id,
                                                "game_state": game_state})
        reply = self.conn.recv_reply(msg_id, timeout_length)
        # reply should be None

        return reply

    def get_move(self, game_state):
        timeout_length = game_state['timeout_length']

        msg_id = self.conn.send_req("get_move", {"game_state": game_state})
        reply = self.conn.recv_reply(msg_id, timeout_length)

        if "error" in reply:
            return reply
        # make sure that the move is a tuple
        try:
            reply["move"] = tuple(reply.get("move"))
        except TypeError as e:
            # This should also exit the remote connection
            reply = {
                "error": type(e).__name__,
                "error_msg": str(e),
            }
        return reply

    def send_exit(self, game_state=None):

        if game_state:
            payload = {'game_state': game_state}
        else:
            payload = {}

        try:
            _logger.info("Sending exit to remote player %r.", self)
            self.conn.send_exit(payload)
        except RemotePlayerSendError:
            _logger.info("Remote Player %r is already dead during exit. Ignoring.", self)

    def _teardown(self):
        pass

    def __del__(self):
        try:
            self.send_exit()
            self._teardown()
        except AttributeError:
            # in case we exit before self.proc or self.zmqconnection have been set
            pass

    def __repr__(self):
        team_name = f" ({self._team_name})" if self._team_name is not None else ""
        return f"RemoteTeam<{self.team_spec}{team_name} on {self.bound_to_address}>"

class SubprocessTeam(RemoteTeam):
    def __init__(self, team_spec, *, zmq_context=None, idx=None, store_output=False):
        zmq_context = default_zmq_context(zmq_context)

        # We bind to a local tcp port with a zmq PAIR socket
        # and start a new subprocess of pelita_player.py
        # that includes the address of that socket and the
        # team_spec as command line arguments.
        # The subprocess will then connect to this address
        # and load the team.

        socket = zmq_context.socket(zmq.PAIR)
        port = socket.bind_to_random_port('tcp://localhost')
        self.bound_to_address = f"tcp://localhost:{port}"
        if idx == 0:
            color='blue'
        elif idx == 1:
            color='red'
        else:
            color=''
        self.proc, self.stdout_path, self.stderr_path = self._call_pelita_player(team_spec, self.bound_to_address,
                                                                color=color, store_output=store_output)

        super().__init__(team_spec, socket)

    def _call_pelita_player(self, team_spec, address, color='', store_output=False):
        """ Starts another process with the same Python executable and runs `team_spec`
        as a standalone client on URL `addr`.
        """
        player = 'pelita.scripts.pelita_player'
        external_call = [sys.executable,
                            '-m',
                            player,
                            'remote-game',
                            team_spec,
                            address]

        _logger.debug("Executing: %r", external_call)
        if store_output == subprocess.DEVNULL:
            return (subprocess.Popen(external_call, stdout=store_output), None, None)
        elif store_output:
            store_path = Path(store_output)
            stdout_path = (store_path / f"{color or team_spec}.out")
            stderr_path = (store_path / f"{color or team_spec}.err")

            # We must run in unbuffered mode to enforce flushing of stdout/stderr,
            # otherwise we may lose some of what is printed
            proc = subprocess.Popen(external_call, stdout=stdout_path.open('w'), stderr=stderr_path.open('w'),
                                    env=dict(os.environ, PYTHONUNBUFFERED='x'))
            return (proc, stdout_path, stderr_path)
        else:
            return (subprocess.Popen(external_call), None, None)

    def _teardown(self):
        if self.proc:
            self.proc.terminate()


class RemoteServerTeam(RemoteTeam):
    """ Start a child process with the given `team_spec` and handle
    communication with it through a zmq.PAIR connection.

    It also does some basic checks for correct return values and tries to
    terminate the child process once it is not needed anymore.

    Parameters
    ----------
    team_spec
        The string to pass as a command line argument to pelita_player
        or the address of a remote player
    team_name
        Overrides the team name
    zmq_context
        A zmq_context (if None, a new one will be created)
    idx
        The team index (currently only used to specify the team’s color)
    store_output
        If store_output is a string it will be interpreted as a path to a
        directory where to store stdout and stderr for the client processes.
        It helps in debugging issues with the clients.
        In the special case of store_output==subprocess.DEVNULL, stdout of
        the remote clients will be suppressed.
    """

    def __init__(self, team_spec, *, team_name=None, zmq_context=None):
        zmq_context = default_zmq_context(zmq_context)

        # We connect to a remote player that is listening
        # on the given team_spec address.
        # We create a new DEALER socket and send a single
        # REQUEST message to the remote address.
        # The remote player will then create a new instance
        # of a player and forward all of our zmq traffic
        # to that player.

        # given a url pelita://hostname:port/path we extract hostname and port and
        # convert it to tcp://hostname:port that we use for the zmq connection
        parsed_url = urlparse(team_spec)
        if parsed_url.port:
            port = parsed_url.port
        else:
            port = PELITA_PORT
        send_addr = f"tcp://{parsed_url.hostname}:{port}"
        self.bound_to_address = send_addr

        socket = zmq_context.socket(zmq.DEALER)
        socket.setsockopt(zmq.LINGER, 0)
        socket.connect(send_addr)
        _logger.info("Connecting zmq.DEALER to remote player at {}.".format(send_addr))

        socket.send_json({"REQUEST": team_spec})

        super().__init__(team_spec, socket)


def make_team(team_spec, team_name=None, zmq_context=None, idx=None, store_output=False):
    """ Creates a Team object for the given team_spec.

    If no zmq_context is passed for a remote team, then a new context
    will be automatically created and returned. Otherwise, the same
    zmq_context (or None) will be returned.

    Parameters
    ----------
    team_spec : callable or str
        A move function or a team_spec that is passed on to pelita_player

    team_name : str, optional
        Optional team name for a local team

    zmq_context : zmq context, optional
        ZMQ context to avoid having to create a new context for every team

    Returns
    -------
    team_player, zmq_context : tuple
        The team class to interact with
        The new ZMQ context

    """
    if callable(team_spec):
        _logger.info("Making a local team for %s", team_spec)
        # wrap the move function in a Team
        if team_name is None:
            team_name = f'local-team ({team_spec.__name__})'
        team_player = Team(team_spec, team_name=team_name)
    elif isinstance(team_spec, str):
        # set up the zmq connections and build a RemoteTeam
        zmq_context = default_zmq_context(zmq_context)
        if team_spec.startswith('pelita://'):
            _logger.info("Making a remote team for %s", team_spec)
            team_player = RemoteServerTeam(team_spec=team_spec, zmq_context=zmq_context)
        else:
            _logger.info("Making a subprocess team for %s", team_spec)
            team_player = SubprocessTeam(team_spec=team_spec, zmq_context=zmq_context, idx=idx, store_output=store_output)
    else:
        raise TypeError(f"Not possible to create team from {team_spec} (wrong type).")

    return team_player, zmq_context


class Bot:
    def __init__(self, *, bot_index,
                          is_on_team,
                          position,
                          initial_position,
                          walls,
                          shape,
                          homezone,
                          food,
                          shaded_food,
                          score,
                          kills,
                          deaths,
                          was_killed,
                          random,
                          graph,
                          round,
                          bot_char,
                          is_blue,
                          team_name,
                          team_time,
                          error_count,
                          is_noisy,
                          bot_turn=None):
        self._bots = None
        self._say = None

        #: The previous positions of this bot including the current one.
        self.track = []

        #: Is this a friendly bot?
        self._is_on_team = is_on_team

        self.random = random
        self.position = tuple(position)
        self._initial_position = tuple(initial_position)
        self.walls = walls

        self.homezone = homezone
        self.food = food
        self.shaded_food = shaded_food
        self.shape = shape
        self.score  = score
        self.kills = kills
        self.deaths = deaths
        self.was_killed = was_killed
        self._bot_index  = bot_index
        self.round = round
        self.char = bot_char
        self.is_blue = is_blue
        self.team_name = team_name
        self.team_time = team_time
        self.error_count = error_count
        self.is_noisy = is_noisy
        self.has_exact_position = not is_noisy
        self.graph = graph

        # The legal positions that the bot can reach from its current position,
        # including the current position.
        self.legal_positions = []

        for direction in [(0, 0), (-1, 0), (1, 0), (0, 1), (0, -1)]:
            new_pos = (position[0] + direction[0],
                       position[1] + direction[1])
            if new_pos not in self.walls:
                self.legal_positions.append(new_pos)

        # Attributes for Bot
        if self._is_on_team:
            assert bot_turn is not None
            self._bot_turn = bot_turn

    @property
    def _team(self):
       """ Both of our bots.
       """
       if self._is_on_team:
           return self._bots['team']
       else:
           return self._bots['enemy']

    @property
    def turn(self):
        """ The turn of our bot. """
        return self._bot_index % 2

    @property
    def other(self):
        """ The other bot in our team. """
        return self._team[1 - self.turn]

    @property
    def enemy(self):
        """ The list of enemy bots
        """
        if not self._is_on_team:
            return self._bots['team']
        else:
            return self._bots['enemy']

    def say(self, text):
        """ Print some text in the graphical interface. """
        # sanitize text so that funny users can't break the GUI
        self._say = sanitize_say(text)

    def _repr_html_(self):
        """ Jupyter-friendly representation. """
        bot = self
        width, height = bot.shape

        with StringIO() as out:
            out.write("<table>")
            for y in range(height):
                out.write("<tr>")
                for x in range(width):
                    if (x, y) in bot.walls:
                        bg = 'style="background-color: {}"'.format(
                            "rgb(94, 158, 217)" if x < width // 2 else
                            "rgb(235, 90, 90)")
                    else:
                        bg = ""
                    out.write("<td %s>" % bg)
                    if (x, y) in bot.walls:
                        out.write("#")
                    if (x, y) in bot.food:
                        out.write('<span style="color: rgb(247, 150, 213)">●</span>')
                    if (x, y) in bot.enemy[0].food:
                        out.write('<span style="color: rgb(247, 150, 213)">●</span>')
                    for idx in range(2):
                        if bot._team[idx].position == (x, y):
                            if idx == bot.turn:
                                out.write('<b>' + str(idx) + '</b>')
                            else:
                                out.write(str(idx))
                    for idx in range(2):
                        if bot.enemy[idx].position == (x, y):
                            out.write(str(idx))

                    out.write("</td>")
                out.write("</tr>")
            out.write("</table>")
            return out.getvalue()

    def __str__(self):
        bot = self

        if bot.is_blue:
            blue = bot if not bot.turn else bot.other
            red = bot.enemy[0]
        else:
            blue = bot.enemy[0]
            red = bot if not bot.turn else bot.other

        bot_positions = [blue.position, red.position, blue.other.position, red.other.position]
        bot_exact = [blue.has_exact_position, red.has_exact_position, blue.other.has_exact_position, red.other.has_exact_position]

        header = ("{blue}{you_blue} vs {red}{you_red}.\n" +
                  "Playing on {col} side. Current turn: {turn}. "+
                  "Bot: {bot_char}. Round: {round}, score: {blue_score}:{red_score}. " +
                  "timeouts: {blue_timeouts}:{red_timeouts}\n").format(
            blue=blue.team_name,
            red=red.team_name,
            turn=bot.turn,
            round=bot.round,
            bot_char=bot.char,
            blue_score=blue.score,
            red_score=red.score,
            col="blue" if bot.is_blue else "red",
            you_blue=" (you)" if bot.is_blue else "",
            you_red=" (you)" if not bot.is_blue else "",
            blue_timeouts=blue.error_count,
            red_timeouts=red.error_count,
        )

        footer = ("Bots: {bots}\nExact: {exact}\nFood: {food}\n").format(
                  bots={BOT_I2N[idx]:pos for idx, pos in enumerate(bot_positions)},
                  exact={BOT_I2N[idx]:state for idx, state in enumerate(bot_exact)},
                  food = bot.food + bot.enemy[0].food)

        with StringIO() as out:
            out.write(header)

            layout = layout_as_str(walls=bot.walls,
                                   food=bot.food + bot.enemy[0].food,
                                   bots=bot_positions,
                                   shape=bot.shape)

            out.write(str(layout))
            out.write(footer)
            return out.getvalue()

    def __repr__(self):
        return f'<Bot: {self.char} (team {"blue" if self.is_blue else "red"}), pos: {self.position}, turn: {self.turn}, round: {self.round}>'


# def make_bots(*, walls, shape, initial_positions, homezone, team, enemy, round, bot_turn, rng, graph):
def make_bots(game_state, *, walls, shape, initial_positions, homezone, rng, graph):
    # print(game_state)

    turn = game_state['turn']
    team_index = turn % 2
    bot_turn = turn // 2
    enemy_index = 1 - team_index

    bots = []
    bots_dict = {}

    for idx, position in enumerate(game_state['bots']):
        tidx = idx % 2
        b = Bot(
                bot_index=idx // 2,
                is_on_team=tidx == team_index,
                score=game_state['score'][tidx],
                deaths=game_state['deaths'][idx],
                kills=game_state['kills'][idx],
                was_killed=game_state['bot_was_killed'][idx],
                is_noisy=game_state['is_noisy'][idx],
                error_count=game_state['error_count'][tidx],
                food=_ensure_list_tuples(game_state['food'][tidx]),
                shaded_food=_ensure_list_tuples(game_state['shaded_food'][tidx]),
                walls=walls,
                shape=shape,
                round=game_state['round'],
                bot_turn=bot_turn,
                bot_char=BOT_I2N[idx],
                random=rng,
                graph=graph,
                position=tuple(game_state['bots'][idx]),
                initial_position=initial_positions[idx],
                is_blue=tidx % 2 == 0,
                homezone=homezone[tidx],
                team_name=game_state['team_names'][tidx],
                team_time=game_state['team_time'][tidx]
        )
        b._bots = bots_dict
        bots.append(b)

    team_bots = [b for b in bots if b._is_on_team]
    enemy_bots = [b for b in bots if not b._is_on_team]

    bots_dict['team'] = team_bots
    bots_dict['enemy'] = enemy_bots

    return team_bots[bot_turn]
