
import collections
from functools import reduce
from io import StringIO
import logging
import random
import subprocess

import zmq

from . import AbstractTeam
from .. import libpelita
from ..exceptions import PlayerDisconnected, PlayerTimeout
from ..simplesetup import ZMQConnection, ZMQConnectionError, ZMQReplyTimeout, ZMQUnreachablePeer, DEAD_CONNECTION_TIMEOUT


_logger = logging.getLogger(__name__)


class Team(AbstractTeam):
    """ Simple class used to register an arbitrary number of (Abstract-)Players.

    Each Player is used to control a Bot in the Universe.

    SimpleTeam transforms the `set_initial` and `get_move` messages
    from the GameMaster into calls to the user-supplied functions.

    Parameters
    ----------
    team_name :
        the name of the team (optional)
    players : functions with signature (datadict, storage) -> move
        the Players who shall join this SimpleTeam
    """
    def __init__(self, *args):
        if not args:
            raise ValueError("No teams given.")

        if isinstance(args[0], str):
            self.team_name = args[0]
            team_move = args[1]
        else:
            self.team_name = ""
            team_move = args[0]

        self._team_move = team_move

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
        #: Storage for the team state
        self._team_state = None
        self._team_game = [None, None]

        #: Storage for the random generator
        self._bot_random = random.Random(game_state['seed'])

        #: Store a history of bot positions
        self._bot_track = [[], []]

        # To make things a little simpler, we also initialise a random generator
        # for all enemy bots

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
        me = make_bots(**game_state)
        me.random = self._bot_random

        team = me._team

        for idx, mybot in enumerate(team):
            # If a bot has been eaten, we reset it’s bot track
            if mybot.has_respawned:
                self._bot_track[idx] = []

        # Add our track
        if len(self._bot_track[me.bot_turn]) == 0:
            self._bot_track[me.bot_turn] = [me.position]

        for idx, mybot in enumerate(team):
            # If the track of any bot is empty,
            # Add its current position
            if me.bot_turn != idx:
                self._bot_track[idx].append(mybot.position)

            mybot.track = self._bot_track[idx][:]

        self._team_game = team
        move, state = self._team_move(self._team_game[me.bot_turn], self._team_state)

        # restore the team state
        self._team_state = state

        return {
            "move": move,
            "say": me._say
        }

    def __repr__(self):
        return "Team(%r, %s)" % (self.team_name, repr(self._team_move))


class RemoteTeam:
    """ Start a child process with the given `team_spec` and handle
    communication with it through a zmq.PAIR connection.

    It also does some basic checks for correct return values and tries to
    terminate the child process once it is not needed anymore.

    Parameters
    ----------
    zmq_context
        A zmq_context (if None, a new one will be created)
    team_spec
        The string to pass as a command line argument to pelita_player
    address
        The zmq address (an address will be chosen randomly, if empty)
    """
    def __init__(self, team_spec, team_name=None, address="tcp://", zmq_context=None, timeout_length=3, idx=None):
        if zmq_context is None:
            zmq_context = zmq.Context()
        socket = zmq_context.socket(zmq.PAIR)
        port = socket.bind_to_random_port('tcp://*')
        self._team_spec = team_spec
        self._team_name = team_name
        self.bound_to_address =f"tcp://localhost:{port}"
        self.zmqconnection = ZMQConnection(socket)
        self.timeout_length = timeout_length
        if idx == 0:
            color='blue'
        if idx == 1:
            color='red'
        self.proc = self._call_pelita_player(team_spec, self.bound_to_address, color=color)

    def _call_pelita_player(self, team_spec, address, color='', dump=None):
        """ Starts another process with the same Python executable,
        the same start script (pelitagame) and runs `team_spec`
        as a standalone client on URL `addr`.
        """
        player = 'pelita.scripts.pelita_player'
        external_call = [libpelita.get_python_process(),
                         '-m',
                         player,
                         team_spec,
                         address,
                         '--color',
                         color]

        _logger.debug("Executing: %r", external_call)
        if dump:
            stdout = Path(dump + '.' + (color or module_spec) + '.out').open('w')
            stderr = Path(dump + '.' + (color or module_spec) + '.err').open('w')
            return (subprocess.Popen(external_call, stdout=stdout, stderr=stderr), stdout, stderr)
        else:
            return (subprocess.Popen(external_call), None, None)

    # TODO
#   def team_name(self):
#       try:
#           self.zmqconnection.send("team_name", {})
#           return self.zmqconnection.recv_timeout(DEAD_CONNECTION_TIMEOUT)
#       except ZMQReplyTimeout:
#           _logger.info("Detected a timeout, returning a string nonetheless.")
#           return "%error%"
#       except ZMQUnreachablePeer:
#           _logger.info("Detected a DeadConnection, returning a string nonetheless.")
#           return "%error%"

    def set_initial(self, team_id, game_state):
        try:
            self.zmqconnection.send("set_initial", {"team_id": team_id,
                                                    "game_state": game_state})
            team_name = self.zmqconnection.recv_timeout(self.timeout_length)
            if team_name:
                self._team_name = team_name
            return team_name
        except ZMQReplyTimeout:
            # answer did not arrive in time
            raise PlayerTimeout()
        except ZMQUnreachablePeer:
            _logger.info("Could not properly send the message. Maybe just a slow client. Ignoring in set_initial.")
        except ZMQConnectionError as e:
            _logger.info("Detected a ConnectionError: %s", e)
            return '%%%s%%' % e

    def get_move(self, game_state, timeout_length=None):
        try:
            self.zmqconnection.send("get_move", {"game_state": game_state})
            reply = self.zmqconnection.recv_timeout(self.timeout_length)
            # make sure it is a dict
            reply = dict(reply)
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
        except ZMQConnectionError:
            raise

    def _exit(self):
        try:
            self.zmqconnection.send("exit", {}, timeout=1)
        except ZMQUnreachablePeer:
            _logger.info("Remote Player %r is already dead during exit. Ignoring.", self)

    def __del__(self):
        self._exit()
        self.proc[0].terminate()

    def __repr__(self):
        team_name = f" ({self._team_name})" if self._team_name else ""
        return f"RemoteTeam<{self._team_spec}{team_name} on {self.bound_to_address}>" 


def make_team(team_spec, team_name=None, zmq_context=None, idx=None):
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
        _logger.debug("Making a local team for %s", team_spec)
        # wrap the move function in a Team
        if team_name is None:
            team_name = 'local-team'
        team_player = Team(team_name, team_spec)
    elif isinstance(team_spec, str):
        _logger.debug("Making a remote team for %s", team_spec)
        # wrap the move function in a Team
        if team_spec.startswith('tcp://'):
            # remote team TODO
            pass
        else:
            # start pelita-player
            if not zmq_context:
                zmq_context = zmq.Context()
            team_player = RemoteTeam(team_spec=team_spec, zmq_context=zmq_context, idx=idx)

    return team_player, zmq_context


def create_homezones(width, height):
    return [
        [(x, y) for x in range(0, width // 2)
                for y in range(0, height)],
        [(x, y) for x in range(width // 2, width)
                for y in range(0, height)]
    ]

def _ensure_tuples(list):
    """ Ensures that an iterable is a list of position tuples. """
    return [tuple(item) for item in list]

class Bot:
    def __init__(self, *, bot_index,
                          is_on_team,
                          position,
                          initial_position,
                          walls,
                          homezone,
                          food,
                          score,
                          random,
                          round,
                          is_blue,
                          team_name,
                          timeout_count,
                          bot_turn=None,
                          has_respawned=None,
                          is_noisy=None):
        self._bots = None
        self._say = None

        #: The previous positions of this bot including the current one.
        self.track = []

        #: Is this a friendly bot?
        self.is_on_team = is_on_team

        self.random = random
        self.position = tuple(position)
        self.initial_position = tuple(initial_position)
        self.walls = _ensure_tuples(walls)

        self.homezone = _ensure_tuples(homezone)
        self.food = _ensure_tuples(food)
        self.score  = score
        self.bot_index  = bot_index
        self.round = round
        self.is_blue = is_blue
        self.team_name = team_name
        self.timeout_count = timeout_count

        # Attributes for Bot
        if self.is_on_team:
            assert has_respawned is not None
            self.has_respawned = has_respawned
            assert bot_turn is not None
            self.bot_turn = bot_turn

        # Attributes for Enemy
        if not self.is_on_team:
            assert is_noisy is not None
            self.is_noisy = is_noisy

    @property
    def legal_moves(self):
        """ The legal moves that the bot can make from its current position,
        including no move at all.
        """
        legal_moves = [(0, 0)]

        for move in [(-1, 0), (1, 0), (0, 1), (0, -1)]:
            new_pos = (self.position[0] + move[0], self.position[1] + move[1])
            if not new_pos in self.walls:
                legal_moves.append(move)

        return legal_moves

    @property
    def legal_positions(self):
        """ The legal positions that the bot can reach from its current position,
        including the current position.
        """
        legal_positions = []

        for move in [(0, 0), (-1, 0), (1, 0), (0, 1), (0, -1)]:
            new_pos = (self.position[0] + move[0], self.position[1] + move[1])
            if not new_pos in self.walls:
                legal_positions.append(new_pos)

        return legal_positions

    @property
    def _team(self):
       """ Both of our bots.
       """
       if self.is_on_team:
           return self._bots['team']
       else:
           return self._bots['enemy']

    @property
    def turn(self):
        """ The turn of our bot. """
        return self.bot_index // 2

    @property
    def other(self):
        """ The other bot in our team. """
        return self._team[1 - self.turn]

    @property
    def enemy(self):
        """ The list of enemy bots
        """
        if not self.is_on_team:
            return self._bots['team']
        else:
            return self._bots['enemy']

    def say(self, text):
        """ Print some text in the graphical interface. """
        self._say = text

    def get_move(self, position):
        """ Return the move needed to get to the given position.

        Raises
        ======
        ValueError
            If the position cannot be reached by a legal move
        """
        direction = (position[0] - self.position[0], position[1] - self.position[1])
        if direction not in self.legal_moves:
            raise ValueError("Cannot reach position %s (would have been: %s)." % (position, direction))
        return direction

    def get_position(self, move):
        """ Return the position reached with the given move

        Raises
        ======
        ValueError
            If the move is not legal.
        """
        if move not in self.legal_moves:
            raise ValueError("Move %s is not legal." % move)
        position = (move[0] + self.position[0], move[1] + self.position[1])
        return position

    @property
    def eaten(self):
        """ True if this bot has been eaten in the last turn. """
        return self._eaten

    def _repr_html_(self):
        """ Jupyter-friendly representation. """
        bot = self
        width = max(bot.walls)[0] + 1
        height = max(bot.walls)[1] + 1

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
                    for idx in range(4):
                        if bot._bots[idx].position == (x, y):
                            if idx == self.bot_index:
                                out.write('<b>' + str(idx) + '</b>')
                            else:
                                out.write(str(idx))
                    out.write("</td>")
                out.write("</tr>")
            out.write("</table>")
            return out.getvalue()

    def __str__(self):
        bot = self
        width = max(bot.walls)[0] + 1
        height = max(bot.walls)[1] + 1

        header = ("{blue}{you_blue} vs {red}{you_red}.\n" +
            "Playing on {col} side. Current turn: {turn}. Round: {round}, score: {blue_score}:{red_score}. " +
            "timeouts: {blue_timeouts}:{red_timeouts}").format(
            blue=bot._bots[0].team_name,
            red=bot._bots[1].team_name,
            turn=bot.turn,
            round=bot.round,
            blue_score=bot._bots[0].score,
            red_score=bot._bots[1].score,
            col="blue" if bot.is_blue else "red",
            you_blue=" (you)" if bot.is_blue else "",
            you_red=" (you)" if not bot.is_blue else "",
            blue_timeouts=bot._bots[0].timeout_count,
            red_timeouts=bot._bots[1].timeout_count,
        )

        with StringIO() as out:
            out.write(header)

            layout = Layout(walls=bot.walls[:],
                            food=bot.food + bot.enemy[0].food,
                            bots=[b.position for b in bot._team],
                            enemy=[e.position for e in bot.enemy])

            out.write(str(layout))
            return out.getvalue()


# def __init__(self, *, bot_index, position, initial_position, walls, homezone, food, is_noisy, score, random, round, is_blue):
def make_bots(*, walls, team, enemy, round, bot_turn, seed=None):
    bots = {}
    team_bots = []
    for idx, position in enumerate(team['bot_positions']):
        b = Bot(bot_index=idx,
            is_on_team=True,
            score=team['score'],
            has_respawned=team['has_respawned'],
            timeout_count=team['timeout_count'],
            food=team['food'],
            walls=walls,
            round=round,
            bot_turn=bot_turn,
            random=seed,
            position=team['bot_positions'][idx],
            initial_position=(0, 0),
            team_name="",
            is_blue=team['team_index'] % 2 == 0,
            homezone=[])
        b._bots = bots
        team_bots.append(b)

    enemy_bots = []
    for idx, position in enumerate(enemy['bot_positions']):
        b = Bot(bot_index=idx,
            is_on_team=False,
            score=enemy['score'],
            is_noisy=enemy['is_noisy'][idx],
            timeout_count=enemy['timeout_count'],
            food=enemy['food'],
            walls=walls,
            round=round,
            random=seed,
            position=enemy['bot_positions'][idx],
            initial_position=(0, 0),
            team_name="",
            is_blue=enemy['team_index'] % 2 == 0,
            homezone=[])
        b._bots = bots
        enemy_bots.append(b)

    bots['team'] = team_bots
    bots['enemy'] = enemy_bots
    return team_bots[bot_turn]


def bots_from_universe(universe, rng, round, team_name, timeout_count):
    """ Creates 4 bots given a universe. """
    return make_bots(walls=[pos for pos, is_wall in universe.maze.items() if is_wall],
                     food=universe.food,
                     positions=[b.current_pos for b in universe.bots],
                     initial_positions=[b.initial_pos for b in universe.bots],
                     score=[t.score for t in universe.teams],
                     is_noisy=[b.noisy for b in universe.bots],
                     rng=rng,
                     round=round,
                     team_name=team_name,
                     timeout_count=timeout_count)

def bot_from_layout(layout, is_blue, score, round, team_name, timeout_count):
    """ Creates 4 bots given a layout. """
    width = max(layout.walls)[0]
    def in_homezone(position, is_blue):
        on_left_side = position[0] < width // 2
        if is_blue:
            return on_left_side
        else:
            return not on_left_side

    team = {
        'bot_positions': layout.bots[:],
        'team_index': 0 if is_blue else 1,
        'score': 0,
        'has_respawned': True,
        'timeout_count': 0,
        'food': [food for food in layout.food if in_homezone(food, is_blue)],
    }
    enemy = {
        'bot_positions': layout.enemy[:],
        'team_index': 0 if not is_blue else 1,
        'score': 0,
        'timeout_count': 0,
        'food': [food for food in layout.food if in_homezone(food, not is_blue)],
        'is_noisy': [False] * len(layout.enemy),
    }

    return make_bots(walls=layout.walls[:],
                     team=team,
                     enemy=enemy,
                     round=None,
                     bot_turn=0,
                     seed=None)


def new_style_team(module):
    """ Looks for a new-style team in `module`.
    """
    # look for a new-style team
    move = getattr(module, "move")
    name = getattr(module, "TEAM_NAME")
    if not callable(move):
        raise TypeError("move is not a function")
    if type(name) is not str:
        raise TypeError("TEAM_NAME is not a string")
    return lambda: Team(name, move)


# @dataclass
class Layout:
    def __init__(self, walls, food, bots, enemy):
        if not food:
            food = []

        if not bots:
            bots = [None, None]

        if not enemy:
            enemy = [None, None]

        # input validation
        for pos in [*food, *bots, *enemy]:
            if pos:
                if len(pos) != 2:
                    raise ValueError("Items must be tuples of length 2.")
                if pos in walls:
                    raise ValueError("Item at %r placed on walls." % (pos,))
                else:
                    walls_width = max(walls)[0] + 1
                    walls_height = max(walls)[1] + 1
                    if not (0 <= pos[0] < walls_width) or not (0 <= pos[1] < walls_height):
                        raise ValueError("Item at %r not in bounds." % (pos,))


        if len(bots) > 2:
            raise ValueError("Too many bots given.")

        self.walls = sorted(walls)
        self.food = sorted(food)
        self.bots = bots
        self.enemy = enemy
        self.initial_positions = self.guess_initial_positions(self.walls)

    def guess_initial_positions(self, walls):
        """ Returns the free positions that are closest to the bottom left and
        top right corner. The algorithm starts searching from (1, -2) and (-2, 1)
        respectively and uses the manhattan distance for judging what is closest.
        On equal distances, a smaller distance in the x value is preferred.
        """
        walls_width = max(walls)[0] + 1
        walls_height = max(walls)[1] + 1

        left_start = (1, walls_height - 2)
        left_initials = []
        right_start = (walls_width - 2, 1)
        right_initials = []

        dist = 0
        while len(left_initials) < 2:
            # iterate through all possible x distances (inclusive)
            for x_dist in range(dist + 1):
                y_dist = dist - x_dist
                pos = (left_start[0] + x_dist, left_start[1] - y_dist)
                # if both coordinates are out of bounds, we stop
                if not (0 <= pos[0] < walls_width) and not (0 <= pos[1] < walls_height):
                    raise ValueError("Not enough free initial positions.")
                # if one coordinate is out of bounds, we just continue
                if not (0 <= pos[0] < walls_width) or not (0 <= pos[1] < walls_height):
                    continue
                # check if the new value is free
                if not pos in walls:
                    left_initials.append(pos)

                if len(left_initials) == 2:
                    break

            dist += 1

        dist = 0
        while len(right_initials) < 2:
            # iterate through all possible x distances (inclusive)
            for x_dist in range(dist + 1):
                y_dist = dist - x_dist
                pos = (right_start[0] - x_dist, right_start[1] + y_dist)
                # if both coordinates are out of bounds, we stop
                if not (0 <= pos[0] < walls_width) and not (0 <= pos[1] < walls_height):
                    raise ValueError("Not enough free initial positions.")
                # if one coordinate is out of bounds, we just continue
                if not (0 <= pos[0] < walls_width) or not (0 <= pos[1] < walls_height):
                    continue
                # check if the new value is free
                if not pos in walls:
                    right_initials.append(pos)

                if len(right_initials) == 2:
                    break

            dist += 1

        # lower indices start further away
        left_initials.reverse()
        right_initials.reverse()
        return left_initials, right_initials

    def merge(self, other):
        """ Merges `self` with the `other` layout.
        """

        if not self.walls:
            self.walls = other.walls
        if self.walls != other.walls:
            raise ValueError("Walls are not equal.")

        self.food += other.food
        # remove duplicates
        self.food = list(set(self.food))

        # update all newer bot positions
        for idx, b in enumerate(other.bots):
            if b:
                self.bots[idx] = b

        # merge all enemies and then take the last 2
        enemies = [e for e in [*self.enemy, *other.enemy] if e is not None]
        self.enemy = enemies[-2:]
        # if self.enemy smaller than 2, we pad with None again
        for _ in range(2 - len(self.enemy)):
            self.enemy.append(None)

        # return our merged self
        return self

    def _repr_html_(self):
        walls = self.walls
        walls_width = max(walls)[0] + 1
        walls_height = max(walls)[1] + 1
        with StringIO() as out:
            out.write("<table>")
            for y in range(walls_height):
                out.write("<tr>")
                for x in range(walls_width):
                    if (x, y) in walls:
                        bg = 'style="background-color: {}"'.format(
                            "rgb(94, 158, 217)" if x < walls_width // 2 else
                            "rgb(235, 90, 90)")
                    elif (x, y) in self.initial_positions[0]:
                        bg = 'style="background-color: #ffffcc"'
                    elif (x, y) in self.initial_positions[1]:
                        bg = 'style="background-color: #ffffcc"'
                    else:
                        bg = ""
                    out.write("<td %s>" % bg)
                    if (x, y) in walls: out.write("#")
                    if (x, y) in self.food: out.write('<span style="color: rgb(247, 150, 213)">●</span>')
                    for idx, pos in enumerate(self.bots):
                        if pos == (x, y):
                            out.write(str(idx))
                    for pos in self.enemy:
                        if pos == (x, y):
                            out.write('E')
                    out.write("</td>")
                out.write("</tr>")
            out.write("</table>")
            return out.getvalue()

    def __str__(self):
        walls = self.walls
        walls_width = max(walls)[0] + 1
        walls_height = max(walls)[1] + 1
        with StringIO() as out:
            out.write('\n')
            # first, print walls and food
            for y in range(walls_height):
                for x in range(walls_width):
                    if (x, y) in walls: out.write('#')
                    elif (x, y) in self.food: out.write('.')
                    else: out.write(' ')
                out.write('\n')
            out.write('\n')
            # print walls and bots

            # Do we have bots/enemies sitting on each other?

            # assign bots to their positions
            bots = {}
            for pos in self.enemy:
                bots[pos] = bots.get(pos, []) + ['E']
            for idx, pos in enumerate(self.bots):
                bots[pos] = bots.get(pos, []) + [str(idx)]
            # strip all None positions from bots
            try:
                bots.pop(None)
            except KeyError:
                pass

            while bots:
                for y in range(walls_height):
                    for x in range(walls_width):
                        if (x, y) in walls: out.write('#')
                        elif (x, y) in bots:
                            elem = bots[(x, y)].pop(0)
                            out.write(elem)
                            # cleanup
                            if len(bots[(x, y)]) == 0:
                                bots.pop((x, y))

                        else: out.write(' ')
                    out.write('\n')
                out.write('\n')
            return out.getvalue()

    def __eq__(self, other):
        return ((self.walls, self.food, self.bots, self.enemy, self.initial_positions) ==
                (other.walls, other.food, other.bots, self.enemy, other.initial_positions))


def create_layout(*layout_strings, food=None, bots=None, enemy=None):
    """ Create a layout from layout strings with additional food, bots and enemy positions.

    Walls must be equal in all layout strings. Food positions will be collected.
    For bots and enemy positions later specifications will overwrite earlier ones.

    Raises
    ======
    ValueError
        If walls are not equal in all layouts
    """

    # layout_strings can be a list of strings or one huge string
    # with many layouts after another
    layouts = [
        load_layout(layout)
        for layout_str in layout_strings
        for layout in split_layout_str(layout_str)
    ]
    merged = reduce(lambda x, y: x.merge(y), layouts)
    additional_layout = Layout(walls=merged.walls, food=food, bots=bots, enemy=enemy)
    merged.merge(additional_layout)
    return merged

def split_layout_str(layout_str):
    """ Turns a layout string containing many layouts into a list
    of simple layouts.
    """
    out = []
    current_layout = []
    for row in layout_str.splitlines():
        stripped = row.strip()
        if not stripped:
            # found an empty line
            # if we have a current_layout, append it to out
            # and reset it
            if current_layout:
                out.append(current_layout)
                current_layout = []
            continue
        # non-empty line: append to current_layout
        current_layout.append(row)

    # We still have a current layout at the end: append
    if current_layout:
        out.append(current_layout)

    return ['\n'.join(l) for l in out]

def load_layout(layout_str):
    """ Loads a *single* (partial) layout from a string. """
    build = []
    width = None
    height = None

    food = []
    bots = [None, None]
    enemy = []

    for row in layout_str.splitlines():
        stripped = row.strip()
        if not stripped:
            continue
        if width is not None:
            if len(stripped) != width:
                raise ValueError("Layout has differing widths.")
        width = len(stripped)
        build.append(stripped)

    height = len(build)
    data=list("".join(build))
    def idx_to_coord(idx):
        """ Maps a 1-D index to a 2-D coord given a width and height. """
        return (idx % width, idx // width)

    # Check that the layout is surrounded with walls
    for idx, char in enumerate(data):
        x, y = idx_to_coord(idx)
        if x == 0 or x == width - 1:
            if not char == '#':
                raise ValueError(f"Layout not surrounded with # at ({x}, {y}).")
        if y == 0 or y == height - 1:
            if not char == '#':
                raise ValueError(f"Layout not surrounded with # at ({x}, {y}).")

    walls = []
    # extract the non-wall values from mesh
    for idx, char in enumerate(data):
        coord = idx_to_coord(idx)
        # We know that each char is only one character, so it is
        # either wall or something else
        if '#' in char:
            walls.append(coord)
        # free: skip
        elif ' ' in char:
            continue
        # food
        elif '.' in char:
            food.append(coord)
        # other
        else:
            if 'E' in char:
                # We can have several undefined enemies
                enemy.append(coord)
            elif '0' in char:
                bots[0] = coord
            elif '1' in char:
                bots[1] = coord
            else:
                raise ValueError("Unknown character %s in maze." % char)

    walls = sorted(walls)
    return Layout(walls, food, bots, enemy)
