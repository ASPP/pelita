"""This is the game module. Written in 2019 in Born by Carlos and Lisa."""

import logging
import math
import os
import subprocess
import sys
import time
from warnings import warn

import zmq

from . import layout
from .base_utils import default_rng
from .exceptions import NoFoodWarning, PelitaBotError, PelitaIllegalGameState
from .gamestate_filters import noiser, relocate_expired_food, update_food_age, in_homezone
from .layout import get_legal_positions, initial_positions
from .network import Controller, RemotePlayerFailure, RemotePlayerRecvTimeout, RemotePlayerSendError, ZMQPublisher
from .spec import GameState, Layout, Pos
from .team import RemoteTeam, make_team
from .viewer import (AsciiViewer, ProgressViewer, ReplayWriter, ReplyToViewer,
                     ResultPrinter)

_logger = logging.getLogger(__name__)
_mswindows = (sys.platform == "win32")


### Global constants
# All constants that are currently not redefinable in setup_game

#: The points a team gets for killing another bot
KILL_POINTS = 5

#: The maximum distance between two bots before noise is applied
SIGHT_DISTANCE = 5

#: The radius for the uniform noise
NOISE_RADIUS = 5

#: The lifetime of food pellets in a shadow in turns
MAX_FOOD_AGE = 30

#: Food pellet shadow distance
SHADOW_DISTANCE = 2

#: Default maze sizes
MSIZE = {
         'small' : (16, 8),
         'normal': (32, 16),
         'big'   : (64, 32),
        }

#: Food pellets (trapped_food, total_food) on left side of the maze for
#  default maze sizes
NFOOD = {
         (16, 8) : (3, 10),
         (32, 16): (10, 30),
         (64, 32): (20, 60),
        }

class TkViewer:
    def __init__(self, *, address, controller, geometry=None, delay=None,
                stop_after=None, stop_after_kill=False, fullscreen=False):
        self.proc = self._run_external_viewer(address, controller, geometry=geometry, delay=delay,
                                              stop_after=stop_after, stop_after_kill=stop_after_kill, fullscreen=fullscreen)

    def _run_external_viewer(self, subscribe_sock, controller, geometry, delay, stop_after, stop_after_kill, fullscreen):
        # Something on OS X prevents Tk from running in a forked process.
        # Therefore we cannot use multiprocessing here. subprocess works, though.
        viewer_args = [ str(subscribe_sock) ]
        if controller:
            viewer_args += ["--controller-address", str(controller)]
        if geometry:
            viewer_args += ["--geometry", "{0}x{1}".format(*geometry)]
        if fullscreen:
            viewer_args += ["--fullscreen"]
        if delay:
            viewer_args += ["--delay", str(delay)]
        if stop_after is not None:
            viewer_args += ["--stop-after", str(stop_after)]
        if stop_after_kill:
            viewer_args += ["--stop-after-kill"]

        tkviewer = 'pelita.scripts.pelita_tkviewer'
        external_call = [sys.executable,
                        '-m',
                        tkviewer] + viewer_args
        _logger.debug("Executing: %r", external_call)
        # os.setsid will keep the viewer from closing when the main process exits
        # a better solution might be to decouple the viewer from the main process
        if _mswindows:
            p = subprocess.Popen(external_call, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        else:
            p = subprocess.Popen(external_call, preexec_fn=os.setsid)
        return p

def controller_await(state, await_action='play_step'):
    """Wait for the controller to receive a action from a viewer

    action can be 'exit' (return True), 'play_setup', 'set_initial' (return True)
    """

    if state['controller']:
        todo = state['controller'].await_action(await_action)
        if todo == 'exit':
            return True
        elif todo in ('play_step', 'set_initial'):
            return False

def run_game(team_specs, *, layout_dict, max_rounds=300,
             rng=None, allow_camping=False, error_limit=5, timeout_length=3,
             viewers=None, store_output=False,
             team_names=(None, None), team_infos=(None, None),
             raise_bot_exceptions=False, print_result=True):
    """ Run a pelita match.

    Parameters
    ----------
    team_specs : list[team0, team1]
              a list specifying the two teams to play the match with. The list
              items team0 and team1 must be either
               - a function with signature move(bot, state) -> (x, y)
                 The function takes a bot object and a state and returns the next
                 position (x, y) of the bot.

               - the path to a Python module that defines at least a function
                 called 'move' (specified as above) and a string TEAM_NAME.

              When a team_spec is a function, a "local" game will be run, when
              they are paths to Python modules, a "remote" game will be run instead.
              See below in section Notes for more details about local and remote games.

    layout_dict : dict
               a dictionary representing a maze, as returned by pelita.layout.parse_layout

    max_rounds : int
              The maximum number of rounds to play before the game is over. Default: 300.

    rng : random.Random | int | None
        random number generator or a seed used to initialize a new one.

    error_limit : int
                   The limit of non fatal errors to reach for a team before the
                   game is over and the team is disqualified. Non fatal errors are
                   timeouts and returning an illegal move. Fatal errors are raising
                   Exceptions. An error_limit of 0 will disable the limit.
                   Default: 5.

    timeout_length : int or float
                  Time in seconds to wait for the move function (or for the remote
                  client) to return. After timeout_length seconds are elapsed a
                  non-fatal error is recorded for the team.

    viewers : list[viewer1, viewer2, ...]
           List of viewers to attach to the game. Implemented viewers: 'ascii',
           'progress', tk'. If None, no viewer is attached.

    store_output : False or str
                if store_output is a string it will be interpreted as a path to a
                directory where to store stdout and stderr for the client processes.
                It helps in debugging issues with the clients.
                In the special case of store_output==subprocess.DEVNULL, stdout of
                the remote clients will be suppressed.

    team_names : tuple(team_name_0, team_name_1)
              a tuple containing the team names. If not given, names will be taken
              from the team module TEAM_NAME variable or from the function name.

    team_info : tuple(team_info_0, team_info_1)
              a tuple containing additional team info.

    raise_bot_exceptions : bool
                    when True, allow teams to raise Exceptions. This is especially
                    useful when running local games, where you typically want to
                    see Exceptions do debug them. When running remote games,
                    raise_bot_exceptions should be False, so that the game can collect
                    the exceptions and cleanly create a game-over state if
                    needed.

    print_result : bool
                when True (default), print the result of the match on the command line

    Notes
    -----

    - remote games
        If teams_specs is a list of two Python modules, a "remote" game will be
        played. This means that the game will create one client subprocess for
        each module. The game communicates with the clients using the local network
        and sends/receives messages in JSON format. The game master will ask for the
        next position of a bot over the network, the clients will call their move
        function to get the next position and will return the position over the
        network. This setup allows for complete isolation of the clients, i.e. they
        can not see or influence each other directly.

    - local games
        If team_specs is a list of two functions, a "local" game will be played. This
        means that the game will get the next position of a bot by calling the
        corresponding move function directly. This mode is particularly useful to play
        many games in the background without a UI, because it skips all the network
        overhead of the remote games.

    """

    # allow exception will force exceptions in the clients to be raised.
    # This flag must be used when using run_game directly, like in tests or
    # in background games

    # we create the initial game state
    state = setup_game(team_specs, layout_dict=layout_dict, max_rounds=max_rounds,
                       allow_camping=allow_camping,
                       error_limit=error_limit, timeout_length=timeout_length,
                       rng=rng, viewers=viewers,
                       store_output=store_output, team_names=team_names,
                       team_infos=team_infos,
                       print_result=print_result)

    # Play the game until it is gameover.
    while state['game_phase'] == 'RUNNING':

        # this is only needed if we have a controller, for example a viewer
        # this function call *blocks* until the viewer has replied
        if controller_await(state):
            # if the controller asks us, we'll exit and stop playing
            break

        # play the next turn
        state = play_turn(state, raise_bot_exceptions=raise_bot_exceptions)

    return state


def setup_viewers(viewers, print_result=True):
    """ Returns a list of viewers from the given strings. """

    viewer_state = {
        'viewers': [],
        'procs': [],
        'controller': None
    }

    for v in viewers:
        if isinstance(v, str):
            viewer = v
            viewer_opts = {}
        else:
            viewer, viewer_opts = v

        if viewer == 'ascii':
            viewer_state['viewers'].append(AsciiViewer())
        elif viewer == 'progress':
            viewer_state['viewers'].append(ProgressViewer())
        elif viewer == 'reply-to':
            viewer_state['viewers'].append(ReplyToViewer(viewer_opts))
        elif viewer == 'write-replay-to':
            viewer_state['viewers'].append(ReplayWriter(open(viewer_opts, 'w')))
        elif viewer == 'publish-to':
            zmq_context = zmq.Context()
            zmq_external_publisher = ZMQPublisher(address=viewer_opts, bind=False, zmq_context=zmq_context)
            viewer_state['viewers'].append(zmq_external_publisher)
        elif viewer == 'tk':
            zmq_context = zmq.Context()
            zmq_publisher = ZMQPublisher(address='tcp://127.0.0.1', zmq_context=zmq_context)
            viewer_state['viewers'].append(zmq_publisher)
            viewer_state['controller'] = Controller(zmq_context=zmq_context)

            _proc = TkViewer(address=zmq_publisher.socket_addr, controller=viewer_state['controller'].socket_addr,
                            stop_after=viewer_opts.get('stop_at'),
                            stop_after_kill=viewer_opts.get('stop_after_kill'),
                            geometry=viewer_opts.get('geometry'),
                            delay=viewer_opts.get('delay'),
                            fullscreen=viewer_opts.get('fullscreen'))

        else:
            raise ValueError(f"Unknown viewer {viewer}.")

    # Add the result printer as the final viewer, if print_result has been given
    if print_result:
        viewer_state['viewers'].append(ResultPrinter())

    return viewer_state


def setup_game(team_specs, *, layout_dict: Layout, max_rounds=300, rng=None,
               allow_camping=False, error_limit=5, timeout_length=3,
               viewers=None, store_output=False,
               team_names=(None, None), team_infos=(None, None),
               raise_bot_exceptions=False, print_result=True) -> GameState:
    """ Generates a game state for the given teams and layout with otherwise default values. """
    if viewers is None:
        viewers = []

    # check that two teams have been given
    if not len(team_specs) == 2:
        raise ValueError("Two teams must be given.")

    # check that the given bot positions are all valid
    # and None of them are None (`parse_layout` returns a None position
    # when fewer than 4 bots are defined)
    if not len(layout_dict['bots']) == 4 or None in layout_dict['bots']:
        raise ValueError("Number of bots in layout must be 4.")

    width, height = layout.wall_dimensions(layout_dict['walls'])
    if not (width, height) == layout_dict["shape"]:
        raise ValueError("layout_dict['walls'] does not match layout_dict['shape'].")

    for idx, pos in enumerate(layout_dict['bots']):
        if pos in layout_dict['walls']:
            raise ValueError(f"Bot {idx} must not be on wall: {pos}.")
        try:
            if len(pos) != 2:
                raise ValueError(f"Bot {idx} must be a valid position: got {pos} instead.")
        except TypeError:
            raise ValueError(f"Bot {idx} must be a valid position: got {pos} instead.")
        if not (0, 0) <= pos < (width, height):
            raise ValueError(f"Bot {idx} is not inside the layout: {pos}.")

    food = split_food(width, layout_dict['food'])
    max_food_age = math.inf if allow_camping else MAX_FOOD_AGE

    # warn if one of the food lists is already empty
    side_no_food = [idx for idx, f in enumerate(food) if len(f) == 0]
    if side_no_food:
        warn(f"Layout has no food for team {side_no_food}.", NoFoodWarning)

    viewer_state = setup_viewers(viewers, print_result=print_result)

    rng = default_rng(rng)

    # Initialize the game state.

    game_state: GameState = {
        ### The layout attributes
        #: Walls. Set of (int, int)
        'walls': set(layout_dict['walls']),

        #: Shape of the maze. (int, int)
        'shape': layout_dict['shape'],

        #: Food per team. List of sets of (int, int)
        'food': food,

        #: Food ages per team. Dict of (int, int) to int
        'food_age': ({}, {}),

        ### Round/turn information
        #: Phase
        'game_phase': 'INIT',

        #: Current bot, int, None
        'turn': None,

        #: Current round, int, None
        'round': None,

        #: Is the game finished? bool
        'gameover': False,

        #: Who won? int, None
        'whowins': None,

        ### Bot/team status
        #: Positions of all bots. List of (int, int)
        'bots': layout_dict['bots'][:],

        #: Score of the teams. List of int
        'score': (0, 0),

        #: Fatal errors
        'fatal_errors': ([], []),

        #: Number of timeouts for a team
        'timeouts': ({}, {}),

        ### Configuration
        #: Maximum number of rounds, int
        'max_rounds': max_rounds,

        #: Time till timeout, int
        'timeout': 3,

        #: Initial timeout, int
        'initial_timeout': 6,

        #: Noise radius, int
        'noise_radius': NOISE_RADIUS,

        #: Sight distance, int
        'sight_distance': SIGHT_DISTANCE,

        #: Max food age
        'max_food_age': max_food_age,

        #: Shadow distance, int
        'shadow_distance': SHADOW_DISTANCE,

        ### Informative

        #: Name of the teams. Tuple of str
        'team_names': team_names,

        #: Additional team info. Tuple of str|None
        'team_infos': team_infos,

        #: Time each team needed, list of float
        'team_time': [0.0, 0.0],

        # List of bot deaths, which counts the number of deaths per bot
        # In other words, deaths[bot_idx] is the number of times the bot
        # bot_idx has been killed until now.
        'deaths': [0] * 4,

        # List of bot kills, which counts the number of kills per bot
        # In other words, kills[bot_idx] is the number of times the bot
        # bot_idx has killed another bot until now.
        'kills': [0] * 4,

        # List of boolean flags weather bot has been eaten since its last move
        'bot_was_killed':  [False]*4,

        # The noisy positions that the bot in `turn` has currently been shown.
        # None, if not noisy
        'noisy_positions':  [None] * 4,

        #: The moves that the bots returned. Keeps only the recent one at the respective bot’s index.
        'requested_moves': [None] * 4,

        #: Messages the bots say. Keeps only the recent one at the respective bot’s index.
        'say': [""] * 4,

        ### Internal
        #: Internal team representation
        'teams': [None] * 2,

        #: Random number generator
        'rng': rng,

        #: Timeout length, int, None
        'timeout_length': timeout_length,

        #: Error limit. A team loses when the limit is reached, int
        'error_limit': error_limit,

        #: Viewers, list
        'viewers': viewer_state['viewers'],

        #: Controller
        'controller': viewer_state['controller']
    }


    # Wait until the controller tells us that it is ready
    # We then can send the initial maze
    # This call *blocks* until the controller replies
    if controller_await(game_state, await_action='set_initial'):
        # controller_await has flagged exit
        # We should return with an error
        game_state['game_phase'] = 'FAILURE'
        return game_state

    # Send maze before team creation.
    # This gives a more fluent UI as it does not have to wait for the clients
    # to answer to the server.
    update_viewers(game_state)

    team_state = setup_teams(team_specs, game_state, store_output=store_output, raise_bot_exceptions=raise_bot_exceptions)
    game_state.update(team_state)

    # Check if the game has finished (might happen if we set it up with max_rounds=0).
    game_state.update(check_gameover(game_state))

    # Send updated game state with team names to the viewers
    update_viewers(game_state)

    if game_state['game_phase'] == 'INIT':
        # All good.
        send_initial(game_state, raise_bot_exceptions=raise_bot_exceptions)
        game_state.update(check_gameover(game_state))

    # send_initial might have changed our game phase to FAILURE or FINISHED
    if game_state['game_phase'] == 'INIT':
        game_state['game_phase'] = 'RUNNING'
    else:
        # exit remote teams in case there was a failure or the game has finished
        # In this case, we also want to update the viewers
        update_viewers(game_state)
        exit_remote_teams(game_state)

    return game_state


def setup_teams(team_specs, game_state, store_output=False, raise_bot_exceptions=False):
    """ Creates the teams according to the `teams`. """

    assert game_state['game_phase'] == 'INIT'

    # we start with a dummy zmq_context
    # make_team will generate and return a new zmq_context,
    # if it is needed for a remote team
    zmq_context = None

    teams = []
    # First, create all teams
    # If a team is a RemoteTeam, this will start a subprocess
    for team_idx, team_spec in enumerate(team_specs):
        team, zmq_context = make_team(team_spec, idx=team_idx, zmq_context=zmq_context, store_output=store_output, team_name=game_state['team_names'][team_idx])
        teams.append(team)

    # Await that the teams signal readiness and get the team name
    initial_timeout = game_state['initial_timeout']
    start = time.monotonic()

    has_remote_teams = any(isinstance(team, RemoteTeam) for team in teams)
    remote_sockets = {}

    if has_remote_teams:
        poll = zmq.Poller()
        for team_idx, team in enumerate(teams):
            if isinstance(team, RemoteTeam):
                poll.register(team.conn.socket, zmq.POLLIN)
                remote_sockets[team.conn.socket] = team_idx

    break_error = False
    while remote_sockets and not break_error:
        timeout_left = int((initial_timeout - time.monotonic() + start) * 1000)
        if timeout_left <= 0:
            break

        # socket -> zmq.POLLIN id
        evts = dict(poll.poll(timeout_left))
        for socket in evts:
            team_idx = remote_sockets[socket]
            team = teams[team_idx]

            try:
                _state = team.wait_ready(timeout=0)
            except (RemotePlayerSendError, RemotePlayerRecvTimeout, RemotePlayerFailure) as e:
                if len(e.args) > 1:
                    game_print(team_idx, f"{type(e).__name__} ({e.args[0]}): {e.args[1]}")
                else:
                    game_print(team_idx, f"{type(e).__name__}: {e}")

                add_fatal_error(game_state, round=None, turn=team_idx, type=e.__class__.__name__, msg=str(e), raise_bot_exceptions=raise_bot_exceptions)
                break_error = True

            del remote_sockets[socket]

    # Handle timeouts
    if not break_error and remote_sockets:
        break_error = True
        for socket, team_idx in remote_sockets.items():
            game_print(team_idx, f"Team '{teams[team_idx].team_spec}' did not start (timeout).")
            add_fatal_error(game_state, round=None, turn=team_idx, type='Timeout', msg='Team did not start (timeout).', raise_bot_exceptions=raise_bot_exceptions)

    # if we encountered an error, the game_phase should have been set to FAILURE

    # Send the initial state to the teams
    team_names = [team.team_name for team in teams]

    team_state = {
        'teams': teams,
        'team_names': team_names,
    }
    return team_state

def send_initial(game_state, raise_bot_exceptions=False):
    assert game_state["game_phase"] == "INIT"

    teams = game_state['teams']

    for team_idx, team in enumerate(teams):
        # NB: Iterating over the teams may set the game_phase to FAILURE
        if game_state['game_phase'] == 'FAILURE':
            break

        try:
            _res = team.set_initial(team_idx, prepare_bot_state(game_state, team_idx))

        except RemotePlayerFailure as e:
            game_print(team_idx, f"{e.error_type}: {e.error_msg}")
            add_fatal_error(game_state, round=None, turn=team_idx, type=e.error_type, msg=e.error_msg, raise_bot_exceptions=raise_bot_exceptions)

        except RemotePlayerSendError:
            game_print(team_idx, "Send error: Remote team unavailable")
            add_fatal_error(game_state, round=None, turn=team_idx, type='Send error', msg='Remote team unavailable', raise_bot_exceptions=raise_bot_exceptions)

        except RemotePlayerRecvTimeout:
            game_print(team_idx, "timeout: Timeout in set initial")
            add_fatal_error(game_state, round=None, turn=team_idx, type='timeout', msg='Timeout in set initial', raise_bot_exceptions=raise_bot_exceptions)


def request_new_position(game_state):
    round = game_state['round']
    turn = game_state['turn']
    team_idx = game_state['turn'] % 2
    _bot_turn = game_state['turn'] // 2
    team = game_state['teams'][team_idx]

    bot_state = prepare_bot_state(game_state)

    try:
        start_time = time.monotonic()
        bot_reply = team.get_move(bot_state)

    except RemotePlayerFailure as e:
        bot_reply = {
            'error': e.error_type,
            'error_msg': e.error_msg
        }

    except RemotePlayerSendError:
        bot_reply = {
            'error': 'Send error',
            'error_msg': 'Remote team unavailable'
        }

    except RemotePlayerRecvTimeout:
        if game_state['error_limit'] != 0 and len(game_state['timeouts'][team_idx]) + 1 >= game_state['error_limit']:
            # We had too many timeouts already. Trigger a fatal_error.
            # If error_limit is 0, the game will go on.
            bot_reply = {
                'error': 'Timeout error',
                'error_msg': 'Too many timeouts'
            }
        else:
            # There was a timeout. Execute a random move
            legal_positions = get_legal_positions(game_state["walls"], game_state["shape"],
                                                game_state["bots"][game_state["turn"]])
            req_position = game_state['rng'].choice(legal_positions)
            game_print(turn, f"Player timeout. Setting a legal position at random: {req_position}")

            bot_reply = {
                'move': req_position
            }
            timeout_event = {
                'type': 'timeout',
                'description': f"Player timeout. Setting a legal position at random: {req_position}"
            }
            game_state['timeouts'][team_idx][(round, turn)] = timeout_event


    duration = time.monotonic() - start_time
    # update the team_time
    game_state['team_time'][team_idx] += duration

    return bot_reply


def prepare_bot_state(game_state, team_idx=None):
    """ Prepares the bot’s game state for the current bot.

    NB: This will update the game_state to store new noisy positions.
    """
    if game_state['game_phase'] == 'INIT':
        # We assume that we are in get_initial phase
        turn = team_idx
        bot_turn = None
        seed = game_state['rng'].randint(0, sys.maxsize)
    elif game_state['game_phase'] == 'FINISHED':
        # Called for remote players in _exit
        turn = team_idx
        bot_turn = None
        seed = None
    elif game_state['game_phase'] == 'RUNNING':
        turn = game_state['turn']
        bot_turn = game_state['turn'] // 2
        seed = None
    else:
        _logger.warning("Got bad game_state in prepare_bot_state")
        return

    bot_position = game_state['bots'][turn]
    own_team = turn % 2
    enemy_team = 1 - own_team
    enemy_positions = game_state['bots'][enemy_team::2]
    noised_positions = noiser(walls=game_state['walls'],
                              shape=game_state['shape'],
                              bot_position=bot_position,
                              enemy_positions=enemy_positions,
                              noise_radius=game_state['noise_radius'],
                              sight_distance=game_state['sight_distance'],
                              rng=game_state['rng'])


    # Update noisy_positions in the game_state
    # reset positions
    game_state['noisy_positions'] = [None] * 4
    noisy_or_none = [
        noisy_pos if is_noisy else None
            for is_noisy, noisy_pos in
            zip(noised_positions['is_noisy'], noised_positions['enemy_positions'])
    ]
    game_state['noisy_positions'][enemy_team::2] = noisy_or_none

    bots = game_state['bots'][:]
    bots[enemy_team::2] = noised_positions['enemy_positions']

    is_noisy = [False for _ in range(4)]
    is_noisy[enemy_team::2] = noised_positions['is_noisy']

    shaded_food_own = list(pos for pos, age in game_state['food_age'][own_team].items()
                       if age > 0)
    shaded_food = [[], []]
    shaded_food[own_team] = shaded_food_own

    bot_state = {
        'bots': bots,
        'score': game_state['score'][:],
        'kills': game_state['kills'][:],
        'deaths': game_state['deaths'][:],
        'bot_was_killed': game_state['bot_was_killed'][:],
        'error_count': [len(e) for e in game_state['timeouts'][:]],
        'food': [list(team_food) for team_food in game_state['food']],
        'shaded_food': shaded_food,
        'team_time': game_state['team_time'][:],
        'is_noisy': is_noisy,
        'round': game_state['round'],
        'turn': turn,
        'timeout_length': game_state['timeout_length'],
    }

    if game_state['game_phase'] == 'INIT':
        bot_state.update({
            'walls': game_state['walls'], # only in initial round
            'shape': game_state['shape'], # only in initial round
            'seed': seed, # only used in set_initial phase
            'max_rounds': game_state['max_rounds'],
            'team_names': game_state['team_names'][:],
        })

    return bot_state


def update_viewers(game_state):
    """ Sends the current game_state to the viewers. """
    viewer_state = prepare_viewer_state(game_state)
    for viewer in game_state['viewers']:
        viewer.show_state(viewer_state)


def prepare_viewer_state(game_state):
    """ Prepares a state that can be sent to the viewers by removing
    date that cannot be serialized (ie. sockets or keys that
    cannot be used in a json object).

    Furthermore, some redundant data is removed when it has
    already been sent at an earlier date.

    Returns
    -------
    viewer_state : dict
       a new state dict
    """
    viewer_state = {}
    viewer_state.update(game_state)

    # Flatten food and food_age
    viewer_state['food'] = list((viewer_state['food'][0] | viewer_state['food'][1]))
    # We must transform the food age dict to a list or we cannot serialise it
    viewer_state['food_age'] = [item for team_food_age in viewer_state['food_age']
                                          for item in team_food_age.items()]

    # game_state["timeouts"] has a tuple as a dict key
    # that cannot be serialized in json.
    # To fix this problem, we only send the current error
    # and add another attribute "num_errors"
    # to the final dict.

    # the key for the current round, turn
    round_turn = (game_state["round"], game_state["turn"])
    viewer_state["timeouts"] = [
        # retrieve the current error or None
        team_errors.get(round_turn)
        for team_errors in game_state["timeouts"]
    ]

    # add the number of errors
    viewer_state["num_errors"] = [
        len(team_errors)
        for team_errors in game_state["timeouts"]
    ]

    # remove unserializable values
    del viewer_state['teams']
    del viewer_state['rng']
    del viewer_state['viewers']
    del viewer_state['controller']

    return viewer_state


def play_turn(game_state: GameState, raise_bot_exceptions=False):
    """ Plays the next turn of the game.

    This function increases the round and turn counters, requests a move
    and returns a new game_state.

    Raises
    ------
    ValueError
        If game_state["game_phase"] != "RUNNING":
    """
    # TODO: Return a copy of the game_state

    # if the game is already over, we return a value error
    if game_state["game_phase"] != "RUNNING":
        raise ValueError("Game is already over!")

    # Now update the round counter
    game_state.update(next_round_turn(game_state))

    turn = game_state['turn']
    round = game_state['round']
    team = turn % 2

    # update food age and relocate expired food for the current team
    game_state.update(update_food_age(game_state, team, SHADOW_DISTANCE))
    game_state.update(relocate_expired_food(game_state, team, SHADOW_DISTANCE))

    position_dict = request_new_position(game_state)

    if "error" in position_dict:
        error_type = position_dict['error']
        error_string = position_dict.get('error_msg', '')

        game_print(turn, f"{error_type}: {error_string}")
        add_fatal_error(game_state, round=game_state['round'], turn=game_state['turn'],
                        type=error_type, msg=error_string,
                        raise_bot_exceptions=raise_bot_exceptions)
        position = None

    else:
        position = position_dict['move']

    if position_dict.get('say'):
        game_state['say'][game_state['turn']] = position_dict['say']
    else:
        game_state['say'][game_state['turn']] = ""

    # If the returned move looks okay, we add it to the list of requested moves
    old_position = game_state['bots'][turn]
    game_state['requested_moves'][turn] = {
        'previous_position': old_position,
        'requested_position': position,
        'success': False # Success is set to true after apply_move
    }

    if game_state["game_phase"] == "RUNNING":
        # ok. we can apply the move for this team
        # try to execute the move and return the new state
        game_state = apply_move(game_state, position)

        # If there was no error, we claim a success in requested_moves
        if (round, turn) not in game_state['timeouts'][team] and not game_state['fatal_errors'][team]:
            game_state['requested_moves'][turn]['success'] = True

    # Send updated game state with team names to the viewers
    update_viewers(game_state)

    # exit remote teams in case we are game over
    if game_state["game_phase"] != "RUNNING":
        exit_remote_teams(game_state)

    return game_state


def apply_bot_kills(game_state):
    state = {}
    state.update(game_state)

    init_positions = initial_positions(state["walls"], state["shape"])

    # we check for kills at the current bot’s position
    # if any bot respawns during this process, its respawn position will be added to the list
    # and be checked as well
    turn = game_state["turn"]
    targets_to_check = [state["bots"][turn]]

    while targets_to_check:
        target_pos = targets_to_check.pop()

        # only the team in the homezone can kill
        ghost_team = 0 if in_homezone(target_pos, 0, state["shape"]) else 1

        bots_on_target = [idx for idx, pos in enumerate(state["bots"]) if pos == target_pos]

        ghosts_on_target = [idx for idx in bots_on_target if idx % 2 == ghost_team]
        pacmen_on_target = [idx for idx in bots_on_target if idx % 2 != ghost_team]

        if not ghosts_on_target:
            # no ghost, no killing
            continue

        for killable_bot in pacmen_on_target:
            _logger.info(f"Bot {killable_bot} was eaten by bots {ghosts_on_target} at {target_pos}.")

            # respawn
            state["bots"][killable_bot] = init_positions[killable_bot]
            _logger.info(f"Bot {killable_bot} reappears at {state['bots'][killable_bot]}.")

            # we need to check the respawn location for cascading kills
            # (see github issue #891 for reasoning and examples)
            # NB: this assumes that initial_positions only returns positions in the respective home zones
            # otherwise this function may never finish
            targets_to_check.append(state['bots'][killable_bot])

            # add points
            state["score"][ghost_team] += KILL_POINTS
            state["deaths"][killable_bot] += 1
            state["kills"][ghosts_on_target[0]] += 1
            state["bot_was_killed"][killable_bot] = True

    return state

def apply_move(gamestate: GameState, bot_position):
    """Plays a single step of a bot by applying the game rules to the game state. The rules are:
    - if the playing team has an error count of >4 or a fatal error they lose
    - a legal step must not be on a wall, else the error count is increased by 1 and a random move is chosen for the bot
    - if a bot lands on an enemy food pellet, it eats it. It cannot eat its own teams’ food
    - if a bot lands on an enemy bot in its own homezone, it kills the enemy
    - if a bot lands on an enemy bot in its enemy’s homezone, it dies
    - when a bot dies, it reappears in its own homezone at the initial position
    - a game ends when max_rounds is exceeded

    Parameters
    ----------
    gamestate : dict
        state of the game before current turn
    turn : int
        index of the current bot. 0, 1, 2, or 3.
    bot_position : tuple
        new coordinates (x, y) of the current bot.

    Returns
    -------
    dict
        state of the game after applying current turn

    """
    # TODO: gamestate should be immutable
    assert gamestate["game_phase"] == "RUNNING"

    # define local variables
    bots = gamestate["bots"]
    turn = gamestate["turn"]
    team = turn % 2
    score = gamestate["score"]
    food = gamestate["food"]
    walls = gamestate["walls"]
    shape = gamestate["shape"]
    food = gamestate["food"]
    n_round = gamestate["round"]
    kills = gamestate["kills"]
    deaths = gamestate["deaths"]
    bot_was_killed = gamestate["bot_was_killed"]

    # reset our own bot_was_killed flag
    bot_was_killed[turn] = False

    # the allowed moves for the current bot
    legal_positions = get_legal_positions(walls, shape, gamestate["bots"][gamestate["turn"]])

    # check if we made a legal move
    if bot_position not in legal_positions:
        previous_position = gamestate["bots"][gamestate["turn"]]
        game_print(turn, f"Illegal position. {previous_position}➔{bot_position} not in legal positions:"
                            f" {sorted(legal_positions)}.")
        add_fatal_error(gamestate, round=n_round, turn=turn, type='IllegalPosition', msg=f"bot{turn}: {previous_position}➔{bot_position}")

    # only execute move if errors not exceeded
    if not gamestate['game_phase'] == "RUNNING":
        return gamestate

    # take step
    bots[turn] = bot_position
    _logger.info(f"Bot {turn} moves to {bot_position}.")
    # then apply rules

    # bot in homezone needs to be a function
    # because a bot position can change multiple times in a turn
    # example: bot is killed and respawns on top of an enemy

    # update food list
    if not in_homezone(bot_position, team, shape):
        if bot_position in food[1 - team]:
            _logger.info(f"Bot {turn} eats food at {bot_position}.")
            food[1 - team].remove(bot_position)
            # This is modifying the old game state
            score[team] = score[team] + 1

    # we check if we killed or have been killed and update the gamestate accordingly
    gamestate.update(apply_bot_kills(gamestate))

    gamestate_new = {
        "food": food,
        "bots": bots,
        "score": score,
        "deaths": deaths,
        "kills": kills,
        "bot_was_killed": bot_was_killed,
        "game_phase": "RUNNING",
    }

    gamestate.update(gamestate_new)

    # Check if this was the last move of the game (final round or food eaten)
    gamestate.update(check_gameover(gamestate))

    return gamestate


def next_round_turn(game_state):
    """ Takes the round and turn from the game state dict and returns
    the round and turn of the next step in a dict.

    Returns
    -------
    dict { 'round' , 'turn' }
        The updated round and turn

    Raises
    ------
    ValueError
        If gamestate['gameover'] is True
    """

    # TODO: This should take a whole game_phase

    if game_state['gameover']:
        raise ValueError("Game is already over")
    turn = game_state['turn']
    round = game_state['round']

    if turn is None and round is None:
        turn = 0
        round = 1
    elif turn is None or round is None:
        raise PelitaIllegalGameState("Bad configuration for turn and round")
    else:
        # if one of turn or round is None bot not both, it is illegal.
        # TODO: fail with a better error message
        turn = turn + 1
        if turn >= 4:
            turn = turn % 4
            round = round + 1

    return {
        'round': round,
        'turn': turn,
    }

def add_fatal_error(game_state, *, round, turn, type, msg, raise_bot_exceptions=False):
    team_idx = turn % 2

    exception_event = {
        'type': type,
        'description': msg,
        'turn': turn,
        'round': round,
    }
    game_state['fatal_errors'][team_idx].append(exception_event)

    if game_state['game_phase'] == 'INIT':
        num_fatal_errors = [len(f) for f in game_state['fatal_errors']]
        if num_fatal_errors[0] > 0 or num_fatal_errors[1] > 0:
            game_state.update({
                'whowins' : -1,
                'gameover' : True,
                'game_phase': 'FAILURE'
            })

    if game_state['game_phase'] == 'RUNNING':
        # If any team has a fatal error, this team loses.
        # If both teams have a fatal error, it’s a draw.
        num_fatal_errors = [len(f) for f in game_state['fatal_errors']]
        if num_fatal_errors[0] == 0 and num_fatal_errors[1] == 0:
            # no one has any fatal errors
            pass
        elif num_fatal_errors[0] > 0 and num_fatal_errors[1] > 0:
            # both teams have fatal errors: it is a draw
            game_state.update({
                'whowins' : 2,
                'gameover' : True,
                'game_phase': 'FINISHED'
            })
        else:
            # one team has fatal errors
            for team in (0, 1):
                if num_fatal_errors[team] > 0:
                    game_state.update({
                        'whowins' : 1 - team,
                        'gameover' : True,
                        'game_phase': 'FINISHED'
                    })

    if raise_bot_exceptions:
        exit_remote_teams(game_state)
        raise PelitaBotError(type, msg)


def check_gameover(game_state):
    """ Checks if this was the final moves or if the errors have exceeded the threshold.

    Returns
    -------
    dict { 'gameover' , 'whowins', 'game_phase' }
        Flags if the game is over and who won it
    """
    if game_state['game_phase'] == 'FAILURE':
        return {
            'whowins' : -1,
            'gameover' : True,
            'game_phase': 'FAILURE'
        }
    if game_state['game_phase'] == 'FINISHED':
        return {
            'whowins' : game_state['whowins'],
            'gameover' : game_state['gameover'],
            'game_phase': 'FINISHED'
        }
    if game_state['game_phase'] == 'INIT':
        next_step = next_round_turn(game_state)
        next_round = next_step['round']

        # Fail if there is not enough food or rounds
        food_left = [len(f) for f in game_state['food']]
        if next_round > game_state['max_rounds'] or any(f == 0 for f in food_left):
            return {
                'whowins': -1,
                'gameover': True,
                'game_phase': 'FAILURE'
            }
        return {
            'whowins' : None,
            'gameover' : False,
            'game_phase': 'INIT'
        }

    # We are in running phase. Check if the food is gone
    # or if we are in the final turn of the last round.

    # will we overshoot the max rounds with the next step?
    next_step = next_round_turn(game_state)
    next_round = next_step['round']

    # count how much food is left for each team
    food_left = [len(f) for f in game_state['food']]
    if next_round > game_state['max_rounds'] or any(f == 0 for f in food_left):
        if game_state['score'][0] > game_state['score'][1]:
            whowins = 0
        elif game_state['score'][0] < game_state['score'][1]:
            whowins = 1
        else:
            whowins = 2
        return {
            'whowins' : whowins,
            'gameover' : True,
            'game_phase': 'FINISHED'
        }

    return {
        'whowins' : None,
        'gameover' : False,
        'game_phase': 'RUNNING'
    }


def exit_remote_teams(game_state):
    # TODO: Should this be the same function in case of an error?
    # TODO: Handle in network?
    """ If the we are gameover, we want the remote teams to shut down. """
    _logger.info("Telling teams to exit.")
    for idx, team in enumerate(game_state['teams']):
        if len(game_state['fatal_errors'][idx]) > 0:
            _logger.info(f"Not sending exit to team {idx} which had a fatal error.")
            # We pretend we already send the exit message, otherwise
            # the team’s __del__ method will do it once more.
            # TODO: Do with state machine
            team._sent_exit = True
            continue
        try:
            team_game_state = prepare_bot_state(game_state, team_idx=idx)
            team.send_exit(team_game_state)
        except AttributeError:
            pass



def split_food(width, food: list[Pos]):
    team_food: tuple[set[Pos], set[Pos]] = (set(), set())
    for pos in food:
        idx = pos[0] // (width // 2)
        team_food[idx].add(pos)
    return team_food


unicode_to_ascii = {
        '➔' : '->'
        }
def game_print(turn, msg):
    allow_unicode = not _mswindows
    if turn % 2 == 0:
        pie = ('\033[94m' + 'ᗧ' + '\033[0m' + ' ') if allow_unicode else ''
        pie += f'blue team, bot {turn // 2}'
    elif turn % 2 == 1:
        pie = ('\033[91m' + 'ᗧ' + '\033[0m' + ' ') if allow_unicode else ''
        pie += f'red team, bot {turn // 2}'
    if not allow_unicode:
        for uchar, achar in unicode_to_ascii.items():
            msg = msg.replace(uchar, achar)
    print(f'{pie}: {msg}')
