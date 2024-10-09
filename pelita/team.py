
import logging
import os
import subprocess
import sys
import traceback
from io import StringIO
from pathlib import Path
from random import Random
from urllib.parse import urlparse

import zmq
import networkx as nx

from . import layout
from .exceptions import PlayerDisconnected, PlayerTimeout
from .layout import layout_as_str, BOT_I2N, wall_dimensions
from .network import ZMQClientError, ZMQConnection, ZMQReplyTimeout, ZMQUnreachablePeer, PELITA_PORT

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

def walls_to_graph(walls):
    """Return a networkx Graph object given the walls of a maze.

    Parameters
    ----------
    walls : set[(x0,y0), (x1,y1), ...]
         a set of wall coordinates

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
    its adjacent squares by making ore single step (up, down, left, or right).
    """
    graph = nx.Graph()
    width, height = wall_dimensions(walls)

    for x in range(width):
        for y in range(height):
            if (x, y) not in walls:
                # this is a free position, get its neighbors
                for delta_x, delta_y in ((1,0), (-1,0), (0,1), (0,-1)):
                    neighbor = (x + delta_x, y + delta_y)
                    # we don't need to check for getting neighbors out of the maze
                    # because our mazes are all surrounded by walls, i.e. our
                    # deltas will not put us out of the maze
                    if neighbor not in walls:
                        # this is a genuine neighbor, add an edge in the graph
                        graph.add_edge((x, y), neighbor)
    return graph



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
    """
    def __init__(self, team_move, *, team_name=""):
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

        Returns
        -------
        Team name : string
            The name of the team

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
        self._graph = walls_to_graph(self._walls).copy(as_view=True)

        return self.team_name

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
        me = make_bots(walls=self._walls,
                       shape=self._shape,
                       initial_positions=self._initial_positions,
                       homezone=self._homezone,
                       team=game_state['team'],
                       enemy=game_state['enemy'],
                       round=game_state['round'],
                       bot_turn=game_state['bot_turn'],
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

        try:
            # request a move from the current bot
            move = self._team_move(team[me._bot_turn], self._state)

            # check that the returned value is a position tuple
            try:
                if len(move) != 2:
                    raise ValueError(f"Function move did not return a valid position: got {move} instead.")
            except TypeError:
                # Convert to ValueError
                raise ValueError(f"Function move did not return a valid position: got {move} instead.") from None
        except Exception as e:
            # Our client had an exception. We print a traceback and
            # return the type of the exception to the server.
            # If this is a remote player, then this will be detected in pelita_player
            # and pelita_player will close the connection automatically.
            traceback.print_exc()
            return {
                "error": (type(e).__name__, str(e)),
            }

        return {
            "move": move,
            "say": me._say
        }

    def _exit(self, game_state=None):
        """ Dummy function. Only needed for `RemoteTeam`. """
        pass

    def __repr__(self):
        return f'Team({self._team_move!r}, {self.team_name!r})'


class RemoteTeam:
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
    def __init__(self, team_spec, *, team_name=None, zmq_context=None, idx=None, store_output=False):
        if zmq_context is None:
            zmq_context = zmq.Context()

        self._team_spec = team_spec
        self._team_name = team_name

        #: Default timeout for a request, unless specified in the game_state
        self._request_timeout = 3

        if team_spec.startswith('pelita://'):
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
            address = "tcp://*"
            self.bound_to_address = address

            socket = zmq_context.socket(zmq.DEALER)
            socket.setsockopt(zmq.LINGER, 0)
            socket.connect(send_addr)
            _logger.info("Connecting zmq.DEALER to remote player at {}.".format(send_addr))

            socket.send_json({"REQUEST": team_spec})
            WAIT_TIMEOUT = 5000
            incoming = socket.poll(timeout=WAIT_TIMEOUT)
            if incoming == zmq.POLLIN:
                ok = socket.recv()
            else:
                # Server did not respond
                raise PlayerTimeout()
            self.proc = None

        else:
            # We bind to a local tcp port with a zmq PAIR socket
            # and start a new subprocess of pelita_player.py
            # that includes the address of that socket and the
            # team_spec as command line arguments.
            # The subprocess will then connect to this address
            # and load the team.

            socket = zmq_context.socket(zmq.PAIR)
            port = socket.bind_to_random_port('tcp://*')
            self.bound_to_address = f"tcp://localhost:{port}"
            if idx == 0:
                color='blue'
            elif idx == 1:
                color='red'
            else:
                color=''
            self.proc = self._call_pelita_player(team_spec, self.bound_to_address,
                                                 color=color, store_output=store_output)

        self.zmqconnection = ZMQConnection(socket)

    def _call_pelita_player(self, team_spec, address, color='', store_output=False):
        """ Starts another process with the same Python executable,
        the same start script (pelitagame) and runs `team_spec`
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
            stdout = (store_path / f"{color or team_spec}.out").open('w')
            stderr = (store_path / f"{color or team_spec}.err").open('w')

            # We must run in unbuffered mode to enforce flushing of stdout/stderr,
            # otherwise we may lose some of what is printed
            proc = subprocess.Popen(external_call, stdout=stdout, stderr=stderr,
                                    env=dict(os.environ, PYTHONUNBUFFERED='x'))
            return (proc, stdout, stderr)
        else:
            return (subprocess.Popen(external_call), None, None)

    @property
    def team_name(self):
        if self._team_name is not None:
            return self._team_name

        try:
            msg_id = self.zmqconnection.send("team_name", {})
            team_name = self.zmqconnection.recv_timeout(msg_id, self._request_timeout)
            if team_name:
                self._team_name = team_name
            return team_name
        except ZMQReplyTimeout:
            _logger.info("Detected a timeout, returning a string nonetheless.")
            return "%error%"
        except ZMQUnreachablePeer:
            _logger.info("Detected a DeadConnection, returning a string nonetheless.")
            return "%error%"

    def set_initial(self, team_id, game_state):
        timeout_length = game_state['timeout_length']
        try:
            msg_id = self.zmqconnection.send("set_initial", {"team_id": team_id,
                                                    "game_state": game_state})
            team_name = self.zmqconnection.recv_timeout(msg_id, timeout_length)
            if team_name:
                self._team_name = team_name
            return team_name
        except ZMQReplyTimeout:
            # answer did not arrive in time
            raise PlayerTimeout()
        except ZMQUnreachablePeer:
            _logger.info("Could not properly send the message. Maybe just a slow client. Ignoring in set_initial.")
        except ZMQClientError as e:
            error_message = e.message
            error_type = e.error_type
            _logger.warning(f"Client connection failed ({error_type}): {error_message}")
            raise PlayerDisconnected(*e.args) from None

    def get_move(self, game_state):
        timeout_length = game_state['timeout_length']
        try:
            msg_id = self.zmqconnection.send("get_move", {"game_state": game_state})
            reply = self.zmqconnection.recv_timeout(msg_id, timeout_length)
            # make sure it is a dict
            reply = dict(reply)
            if "error" in reply:
                return reply
            # make sure that the move is a tuple
            reply["move"] = tuple(reply.get("move"))
            return reply
        except ZMQReplyTimeout:
            # answer did not arrive in time
            raise PlayerTimeout()
        except TypeError:
            # if we could not convert into a tuple or dict (e.g. bad reply)
            return None
        except ZMQUnreachablePeer:
            # if the remote connection is closed
            raise PlayerDisconnected()
        except ZMQClientError:
            raise

    def _exit(self, game_state=None):
        # We only want to exit once.
        if getattr(self, '_sent_exit', False):
            return

        if game_state:
            payload = {'game_state': game_state}
        else:
            payload = {}

        try:
            # TODO: make zmqconnection stateful. set flag when already disconnected
            # For now, we simply check the state of the socket so that we do not send
            # over an already closed socket.
            if self.zmqconnection.socket.closed:
                return
            # TODO: Include final state with exit message
            self.zmqconnection.send("exit", payload, timeout=1)
            self._sent_exit = True
        except ZMQUnreachablePeer:
            _logger.info("Remote Player %r is already dead during exit. Ignoring.", self)

    def __del__(self):
        try:
            self._exit()
            if self.proc:
                self.proc[0].terminate()
        except AttributeError:
            # in case we exit before self.proc or self.zmqconnection have been set
            pass

    def __repr__(self):
        team_name = f" ({self._team_name})" if self._team_name else ""
        return f"RemoteTeam<{self._team_spec}{team_name} on {self.bound_to_address}>"


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
        _logger.info("Making a remote team for %s", team_spec)
        # set up the zmq connections and build a RemoteTeam
        if not zmq_context:
            zmq_context = zmq.Context()
        team_player = RemoteTeam(team_spec=team_spec, zmq_context=zmq_context, idx=idx, store_output=store_output)
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
        self.graph = graph

        # The legal positions that the bot can reach from its current position,
        # including the current position.
        self.legal_positions = []

        for direction in [(0, 0), (-1, 0), (1, 0), (0, 1), (0, -1)]:
            new_pos = (position[0] + direction[0],
                       position[1] + direction[1])
            if not new_pos in self.walls:
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
        self._say = text

    # def get_direction(self, position):
        # """ Return the direction needed to get to the given position.

        # Raises
        # ======
        # ValueError
            # If the position cannot be reached by a legal move
        # """
        # direction = (position[0] - self.position[0], position[1] - self.position[1])
        # if direction not in self.legal_directions:
            # raise ValueError("Cannot reach position %s (would have been: %s)." % (position, direction))
        # return direction

    # def get_position(self, direction):
        # """ Return the position reached with the given direction

        # Raises
        # ======
        # ValueError
            # If the direction is not legal.
        # """
        # if direction not in self.legal_directions:
            # raise ValueError(f"Direction {direction} is not legal.")
        # position = (direction[0] + self.position[0], direction[1] + self.position[1])
        # return position


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
                    if (x, y) in bot.walls: out.write("#")
                    if (x, y) in bot.food: out.write('<span style="color: rgb(247, 150, 213)">●</span>')
                    if (x, y) in bot.enemy[0].food: out.write('<span style="color: rgb(247, 150, 213)">●</span>')
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
        bot_noise = [blue.is_noisy, red.is_noisy, blue.other.is_noisy, red.other.is_noisy]

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

        footer = ("Bots: {bots}\nNoisy: {noise}\nFood: {food}\n").format(
                  bots={BOT_I2N[idx]:pos for idx, pos in enumerate(bot_positions)},
                  noise={BOT_I2N[idx]:state for idx, state in enumerate(bot_noise)},
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


# def __init__(self, *, bot_index, position, initial_position, walls, homezone, food, is_noisy, score, random, round, is_blue):
def make_bots(*, walls, shape, initial_positions, homezone, team, enemy, round, bot_turn, rng, graph):
    bots = {}

    team_index = team['team_index']
    enemy_index = enemy['team_index']

    team_initial_positions = initial_positions[team_index::2]
    enemy_initial_positions = initial_positions[enemy_index::2]

    team_bots = []
    for idx, position in enumerate(team['bot_positions']):
        b = Bot(bot_index=idx,
            is_on_team=True,
            score=team['score'],
            deaths=team['deaths'][idx],
            kills=team['kills'][idx],
            was_killed=team['bot_was_killed'][idx],
            is_noisy=False,
            error_count=team['error_count'],
            food=_ensure_list_tuples(team['food']),
            shaded_food=_ensure_list_tuples(team['shaded_food']),
            walls=walls,
            shape=shape,
            round=round,
            bot_turn=bot_turn,
            bot_char=BOT_I2N[team_index + idx*2],
            random=rng,
            graph=graph,
            position=team['bot_positions'][idx],
            initial_position=team_initial_positions[idx],
            is_blue=team_index % 2 == 0,
            homezone=homezone[team_index],
            team_name=team['name'],
            team_time=team['team_time'])
        b._bots = bots
        team_bots.append(b)

    enemy_bots = []
    for idx, position in enumerate(enemy['bot_positions']):
        b = Bot(bot_index=idx,
            is_on_team=False,
            score=enemy['score'],
            kills=enemy['kills'][idx],
            deaths=enemy['deaths'][idx],
            was_killed=enemy['bot_was_killed'][idx],
            is_noisy=enemy['is_noisy'][idx],
            error_count=enemy['error_count'],
            food=_ensure_list_tuples(enemy['food']),
            shaded_food=[],
            walls=walls,
            shape=shape,
            round=round,
            bot_char = BOT_I2N[team_index + idx*2],
            random=rng,
            graph=graph,
            position=enemy['bot_positions'][idx],
            initial_position=enemy_initial_positions[idx],
            is_blue=enemy_index % 2 == 0,
            homezone=homezone[enemy_index],
            team_name=enemy['name'],
            team_time=enemy['team_time'])
        b._bots = bots
        enemy_bots.append(b)

    bots['team'] = team_bots
    bots['enemy'] = enemy_bots
    return team_bots[bot_turn]

