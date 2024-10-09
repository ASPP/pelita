"""This is the game module. Written in 2019 in Born by Carlos and Lisa."""

import logging
import os
import subprocess
import sys
import time
import math
from warnings import warn

from . import layout
from .exceptions import FatalException, NonFatalException, NoFoodWarning, PlayerTimeout
from .gamestate_filters import noiser, update_food_age, relocate_expired_food
from .layout import initial_positions, get_legal_positions
from .network import setup_controller, ZMQPublisher
from .base_utils import default_rng
from .team import make_team
from .viewer import ProgressViewer, AsciiViewer, ReplyToViewer, ReplayWriter, ResultPrinter

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
SHADOW_DISTANCE = 1

#: Proportion of layouts with dead ends
DEAD_ENDS = 0.25

class TkViewer:
    def __init__(self, *, address, controller, geometry=None, delay=None, stop_after=None, fullscreen=False):
        self.proc = self._run_external_viewer(address, controller, geometry=geometry, delay=delay, stop_after=stop_after, fullscreen=fullscreen)

    def _run_external_viewer(self, subscribe_sock, controller, geometry, delay, stop_after, fullscreen):
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

def controller_exit(state, await_action='play_step'):
    """Wait for the controller to receive a action from a viewer

    action can be 'exit' (return True), 'play_setup', 'set_initial' (return True)
    """

    if state['controller']:
        todo = state['controller'].await_action(await_action)
        if todo == 'exit':
            return True
        elif todo in ('play_step', 'set_initial'):
            return False

def run_game(team_specs, *, layout_dict, layout_name="", max_rounds=300,
             rng=None, allow_camping=False, error_limit=5, timeout_length=3,
             viewers=None, viewer_options=None, store_output=False,
             team_names=(None, None), team_infos=(None, None),
             allow_exceptions=False, print_result=True):
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

    layout_name : str
               a name for the layout (will be used in the UI).

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

    viewer_options : do not use!

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

    allow_exceptions : bool
                    when True, allow teams to raise Exceptions. This is especially
                    useful when running local games, where you typically want to
                    see Exceptions do debug them. When running remote games,
                    allow_exceptions should be False, so that the game can collect
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
    state = setup_game(team_specs, layout_dict=layout_dict,
                       layout_name=layout_name, max_rounds=max_rounds,
                       allow_camping=allow_camping,
                       error_limit=error_limit, timeout_length=timeout_length,
                       rng=rng, viewers=viewers,
                       viewer_options=viewer_options,
                       store_output=store_output, team_names=team_names,
                       team_infos=team_infos,
                       print_result=print_result)

    # Play the game until it is gameover.
    while not state.get('gameover'):

        # this is only needed if we have a controller, for example a viewer
        # this function call *blocks* until the viewer has replied
        if controller_exit(state):
            # if the controller asks us, we'll exit and stop playing
            break

        # play the next turn
        state = play_turn(state, allow_exceptions=allow_exceptions)

    return state


def setup_viewers(viewers=None, options=None, print_result=True):
    """ Returns a list of viewers from the given strings. """
    if viewers is None:
        viewers = []

    if options is None:
        options = {}

    zmq_publisher = None

    viewer_state = {
        'viewers': [],
        'procs': [],
        'controller': None
    }

    for viewer in viewers:
        if viewer == 'ascii':
            viewer_state['viewers'].append(AsciiViewer())
        elif viewer == 'progress':
            viewer_state['viewers'].append(ProgressViewer())
        elif len(viewer) == 2 and viewer[0] == 'reply-to':
            viewer_state['viewers'].append(ReplyToViewer(viewer[1]))
        elif len(viewer) == 2 and viewer[0] == 'write-replay-to':
            viewer_state['viewers'].append(ReplayWriter(open(viewer[1], 'w')))
        elif viewer in ('tk', 'tk-no-sync'):
            if not zmq_publisher:
                zmq_publisher = ZMQPublisher(address='tcp://127.0.0.1')
                viewer_state['viewers'].append(zmq_publisher)
            if viewer == 'tk':
                viewer_state['controller'] = setup_controller()
            if viewer_state['controller']:
                proc = TkViewer(address=zmq_publisher.socket_addr, controller=viewer_state['controller'].socket_addr,
                                stop_after=options.get('stop_at'),
                                geometry=options.get('geometry'),
                                delay=options.get('delay'),
                                fullscreen=options.get('fullscreen'))
            else:
                proc = TkViewer(address=zmq_publisher.socket_addr, controller=None,
                                stop_after=options.get('stop_at'),
                                geometry=options.get('geometry'),
                                delay=options.get('delay'),
                                fullscreen=options.get('fullscreen'))

        else:
            raise ValueError(f"Unknown viewer {viewer}.")

    # Add the result printer as the final viewer, if print_result has been given
    if print_result:
        viewer_state['viewers'].append(ResultPrinter())

    return viewer_state


def setup_game(team_specs, *, layout_dict, max_rounds=300, layout_name="", rng=None,
               allow_camping=False, error_limit=5, timeout_length=3,
               viewers=None, viewer_options=None, store_output=False,
               team_names=(None, None), team_infos=(None, None),
               allow_exceptions=False, print_result=True):
    """ Generates a game state for the given teams and layout with otherwise default values. """

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
        raise ValueError(f"layout_dict['walls'] does not match layout_dict['shape'].")

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

    viewer_state = setup_viewers(viewers, options=viewer_options, print_result=print_result)

    rng = default_rng(rng)

    # Initialize the game state.

    game_state = dict(
        ### The layout attributes
        #: Walls. Set of (int, int)
        walls=set(layout_dict['walls']),

        #: Shape of the maze. (int, int)
        shape=layout_dict['shape'],

        #: Food per team. List of sets of (int, int)
        food=food,

        #: Food ages per team. Dict of (int, int) to int
        food_age=[{}, {}],

        ### Round/turn information
        #: Current bot, int, None
        turn=None,

        #: Current round, int, None
        round=None,

        #: Is the game finished? bool
        gameover=False,

        #: Who won? int, None
        whowins=None,

        ### Bot/team status
        #: Positions of all bots. List of (int, int)
        bots=layout_dict['bots'][:],

        #: Score of the teams. List of int
        score=[0] * 2,

        #: Fatal errors
        fatal_errors=[[], []],

        #: Errors
        errors=[{}, {}],

        ### Configuration
        #: Maximum number of rounds, int
        max_rounds=max_rounds,

        #: Time till timeout, int
        timeout=3,

        #: Noise radius, int
        noise_radius=NOISE_RADIUS,

        #: Sight distance, int
        sight_distance=SIGHT_DISTANCE,

        #: Max food age
        max_food_age=max_food_age,

        #: Shadow distance, int
        shadow_distance=SHADOW_DISTANCE,

        ### Informative
        #: Name of the layout, str
        layout_name=layout_name,

        #: Name of the teams. Tuple of str
        team_names=team_names,

        #: Additional team info. Tuple of str|None
        team_infos=team_infos,

        #: Time each team needed, list of float
        team_time=[0, 0],

        # List of bot deaths, which counts the number of deaths per bot
        # In other words, deaths[bot_idx] is the number of times the bot
        # bot_idx has been killed until now.
        deaths = [0]*4,

        # List of bot kills, which counts the number of kills per bot
        # In other words, kills[bot_idx] is the number of times the bot
        # bot_idx has killed another bot until now.
        kills = [0]*4,

        # List of boolean flags weather bot has been eaten since its last move
        bot_was_killed = [False]*4,

        # The noisy positions that the bot in `turn` has currently been shown.
        # None, if not noisy
        noisy_positions = [None] * 4,

        #: The moves that the bots returned. Keeps only the recent one at the respective bot’s index.
        requested_moves=[None] * 4,

        #: Messages the bots say. Keeps only the recent one at the respective bot’s index.
        say=[""] * 4,

        ### Internal
        #: Internal team representation
        teams=[None] * 2,

        #: Random number generator
        rng=rng,

        #: Timeout length, int, None
        timeout_length=timeout_length,

        #: Error limit. A team loses when the limit is reached, int
        error_limit=error_limit,

        #: Viewers, list
        viewers=viewer_state['viewers'],

        #: Controller
        controller=viewer_state['controller']
    )

    # Wait until the controller tells us that it is ready
    # We then can send the initial maze
    # This call *blocks* until the controller replies
    if controller_exit(game_state, await_action='set_initial'):
        return game_state

    # Send maze before team creation.
    # This gives a more fluent UI as it does not have to wait for the clients
    # to answer to the server.
    update_viewers(game_state)

    team_state = setup_teams(team_specs, game_state, store_output=store_output, allow_exceptions=allow_exceptions)
    game_state.update(team_state)

    # Check if one of the teams has already generate a fatal error
    # or if the game has finished (might happen if we set it up with max_rounds=0).
    game_state.update(check_gameover(game_state, detect_final_move=True))

    # Send updated game state with team names to the viewers
    update_viewers(game_state)

    # exit remote teams in case we are game over
    check_exit_remote_teams(game_state)

    return game_state


def setup_teams(team_specs, game_state, store_output=False, allow_exceptions=False):
    """ Creates the teams according to the `teams`. """

    # we start with a dummy zmq_context
    # make_team will generate and return a new zmq_context,
    # if it is needed for a remote team
    zmq_context = None

    teams = []
    # First, create all teams
    # If a team is a RemoteTeam, this will start a subprocess
    for idx, team_spec in enumerate(team_specs):
        team, zmq_context = make_team(team_spec, idx=idx, zmq_context=zmq_context, store_output=store_output, team_name=game_state['team_names'][idx])
        teams.append(team)

    # Send the initial state to the teams and await the team name (if the teams are local, the name can be get from the game_state directly
    team_names = []
    for idx, team in enumerate(teams):
        try:
            team_name = team.set_initial(idx, prepare_bot_state(game_state, idx))
        except (FatalException, PlayerTimeout) as e:
            # TODO: Not sure if PlayerTimeout should let the other payer win.
            # It could simply be a network problem.
            if allow_exceptions: raise
            exception_event = {
                'type': e.__class__.__name__,
                'description': str(e),
                'turn': idx,
                'round': None,
            }
            game_state['fatal_errors'][idx].append(exception_event)
            if len(e.args) > 1:
                game_print(idx, f"{type(e).__name__} ({e.args[0]}): {e.args[1]}")
                team_name = f"%%%{e.args[0]}%%%"
            else:
                game_print(idx, f"{type(e).__name__}: {e}")
                team_name = "%%%error%%%"
        team_names.append(team_name)

    team_state = {
        'teams': teams,
        'team_names': team_names
    }
    return team_state


def request_new_position(game_state):
    team = game_state['turn'] % 2
    bot_turn = game_state['turn'] // 2
    move_fun = game_state['teams'][team]

    bot_state = prepare_bot_state(game_state)


    start_time = time.monotonic()

    new_position = move_fun.get_move(bot_state)

    duration = time.monotonic() - start_time
    # update the team_time
    game_state['team_time'][team] += duration

    return new_position


def prepare_bot_state(game_state, idx=None):
    """ Prepares the bot’s game state for the current bot.

    """

    bot_initialization = game_state.get('turn') is None and idx is not None
    bot_finalization = game_state.get('turn') is not None and idx is not None

    if bot_initialization:
        # We assume that we are in get_initial phase
        turn = idx
        bot_turn = None
        seed = game_state['rng'].randint(0, sys.maxsize)
    elif bot_finalization:
        # Called for remote players in _exit
        turn = idx
        bot_turn = None
        seed = None
    else:
        turn = game_state['turn']
        bot_turn = game_state['turn'] // 2
        seed = None

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
    shaded_food = list(pos for pos, age in game_state['food_age'][own_team].items()
                       if age > 0)

    team_state = {
        'team_index': own_team,
        'bot_positions': game_state['bots'][own_team::2],
        'score': game_state['score'][own_team],
        'kills': game_state['kills'][own_team::2],
        'deaths': game_state['deaths'][own_team::2],
        'bot_was_killed': game_state['bot_was_killed'][own_team::2],
        'error_count': len(game_state['errors'][own_team]),
        'food': list(game_state['food'][own_team]),
        'shaded_food': shaded_food,
        'name': game_state['team_names'][own_team],
        'team_time': game_state['team_time'][own_team]
    }

    enemy_state = {
        'team_index': enemy_team,
        'bot_positions': noised_positions['enemy_positions'],
        'is_noisy': noised_positions['is_noisy'],
        'score': game_state['score'][enemy_team],
        'kills': game_state['kills'][enemy_team::2],
        'deaths': game_state['deaths'][enemy_team::2],
        'bot_was_killed': game_state['bot_was_killed'][enemy_team::2],
        'error_count': 0, # TODO. Could be left out for the enemy
        'food': list(game_state['food'][enemy_team]),
        'shaded_food': [],
        'name': game_state['team_names'][enemy_team],
        'team_time': game_state['team_time'][enemy_team]
    }

    bot_state = {
        'team': team_state,
        'enemy': enemy_state,
        'round': game_state['round'],
        'bot_turn': bot_turn,
        'timeout_length': game_state['timeout_length'],
        'max_rounds': game_state['max_rounds'],
    }

    if bot_initialization:
        bot_state.update({
            'walls': game_state['walls'], # only in initial round
            'shape': game_state['shape'], # only in initial round
            'seed': seed # only used in set_initial phase
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

    # game_state["errors"] has a tuple as a dict key
    # that cannot be serialized in json.
    # To fix this problem, we only send the current error
    # and add another attribute "num_errors"
    # to the final dict.

    # the key for the current round, turn
    round_turn = (game_state["round"], game_state["turn"])
    viewer_state["errors"] = [
        # retrieve the current error or None
        team_errors.get(round_turn)
        for team_errors in game_state["errors"]
    ]

    # add the number of errors
    viewer_state["num_errors"] = [
        len(team_errors)
        for team_errors in game_state["errors"]
    ]

    # remove unserializable values
    del viewer_state['teams']
    del viewer_state['rng']
    del viewer_state['viewers']
    del viewer_state['controller']

    return viewer_state


def play_turn(game_state, allow_exceptions=False):
    """ Plays the next turn of the game.

    This function increases the round and turn counters, requests a move
    and returns a new game_state.

    Raises
    ------
    ValueError
        If gamestate['gameover'] is True
    """
    # TODO: Return a copy of the game_state

    # if the game is already over, we return a value error
    if game_state['gameover']:
        raise ValueError("Game is already over!")

    # Now update the round counter
    game_state.update(next_round_turn(game_state))

    turn = game_state['turn']
    round = game_state['round']
    team = turn % 2

    # update food age and relocate expired food for the current team
    game_state.update(update_food_age(game_state, team, SHADOW_DISTANCE))
    game_state.update(relocate_expired_food(game_state, team, SHADOW_DISTANCE))

    # request a new move from the current team
    try:
        position_dict = request_new_position(game_state)
        if "error" in position_dict:
            error_type, error_string = position_dict['error']
            raise FatalException(f"Exception in client ({error_type}): {error_string}")
        try:
            position = tuple(position_dict['move'])
        except TypeError as e:
            raise NonFatalException(f"Type error {e}")

        if position_dict.get('say'):
            game_state['say'][game_state['turn']] = position_dict['say']
        else:
            game_state['say'][game_state['turn']] = ""
    except FatalException as e:
        if allow_exceptions: raise
        # FatalExceptions (such as PlayerDisconnect) should immediately
        # finish the game
        exception_event = {
            'type': e.__class__.__name__,
            'description': str(e),
            'turn': game_state['turn'],
            'round': game_state['round'],
        }
        game_state['fatal_errors'][team].append(exception_event)
        position = None
        game_print(turn, f"{type(e).__name__}: {e}")
    except NonFatalException as e:
        if allow_exceptions: raise
        # NonFatalExceptions (such as Timeouts and ValueErrors in the JSON handling)
        # are collected and added to team_errors
        exception_event = {
            'type': e.__class__.__name__,
            'description': str(e)
        }
        game_state['errors'][team][(round, turn)] = exception_event
        position = None
        game_print(turn, f"{type(e).__name__}: {e}")

    # If the returned move looks okay, we add it to the list of requested moves
    old_position = game_state['bots'][turn]
    game_state['requested_moves'][turn] = {
        'previous_position': old_position,
        'requested_position': position,
        'success': False # Success is set to true after apply_move
    }

    # Check if a team has exceeded their maximum number of errors
    # (we do not want to apply the move in this case)
    # Note: Since we already updated the move counter, we do not check anymore,
    # if the game has exceeded its rounds.
    game_state.update(check_gameover(game_state))

    if not game_state['gameover']:
        # ok. we can apply the move for this team
        # try to execute the move and return the new state
        game_state = apply_move(game_state, position)

        # If there was no error, we claim a success in requested_moves
        if (round, turn) not in game_state["errors"][team]:
            game_state['requested_moves'][turn]['success'] = True

        # Check again, if we had errors or if this was the last move of the game (final round or food eaten)
        game_state.update(check_gameover(game_state, detect_final_move=True))

    # Send updated game state with team names to the viewers
    update_viewers(game_state)

    # exit remote teams in case we are game over
    check_exit_remote_teams(game_state)

    return game_state


def apply_move(gamestate, bot_position):
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
    # TODO is a timeout counted as an error?
    # define local variables
    bots = gamestate["bots"]
    turn = gamestate["turn"]
    team = turn % 2
    enemy_idx = (1, 3) if team == 0 else (0, 2)
    gameover = gamestate["gameover"]
    score = gamestate["score"]
    food = gamestate["food"]
    walls = gamestate["walls"]
    shape = gamestate["shape"]
    food = gamestate["food"]
    n_round = gamestate["round"]
    kills = gamestate["kills"]
    deaths = gamestate["deaths"]
    bot_was_killed = gamestate["bot_was_killed"]
    fatal_error = True if gamestate["fatal_errors"][team] else False
    #TODO how are fatal errors passed to us? dict with same structure as regular errors?
    #TODO do we need to communicate that fatal error was the reason for game over in any other way?


    # reset our own bot_was_killed flag
    bot_was_killed[turn] = False

    # previous errors
    team_errors = gamestate["errors"][team]

    # the allowed moves for the current bot
    legal_positions = get_legal_positions(walls, shape, gamestate["bots"][gamestate["turn"]])

    # unless we have already made an error, check if we made a legal move
    if not (n_round, turn) in team_errors:
        if bot_position not in legal_positions:
            error_dict = {
                "reason": 'illegal move',
                "bot_position": bot_position
                }
            # add the error to the team’s errors
            game_print(turn, f"Illegal position. {bot_position} not in legal positions: {sorted(legal_positions)}.")
            team_errors[(n_round, turn)] = error_dict

    # only execute move if errors not exceeded
    gamestate.update(check_gameover(gamestate))
    if gamestate['gameover']:
        return gamestate

    # Now check if we must make a random move
    if (n_round, turn) in team_errors:
        # There was an error for this round and turn
        # but the game is not over.
        # We execute a random move
        bot_position = gamestate['rng'].choice(legal_positions)
        game_print(turn, f"Setting a legal position at random: {bot_position}")

    # take step
    bots[turn] = bot_position
    _logger.info(f"Bot {turn} moves to {bot_position}.")
    # then apply rules
    # is bot in home or enemy territory
    boundary = gamestate['shape'][0] / 2
    if team == 0:
        bot_in_homezone = bot_position[0] < boundary
    elif team == 1:
        bot_in_homezone = bot_position[0] >= boundary
    # update food list
    if not bot_in_homezone:
        if bot_position in food[1 - team]:
            _logger.info(f"Bot {turn} eats food at {bot_position}.")
            food[1 - team].remove(bot_position)
            # This is modifying the old game state
            score[team] = score[team] + 1
    # check if we killed someone
    if bot_in_homezone:
        killed_enemies = [idx for idx in enemy_idx if bot_position == bots[idx]]
        for enemy_idx in killed_enemies:
            _logger.info(f"Bot {turn} eats enemy bot {enemy_idx} at {bot_position}.")
            score[team] = score[team] + KILL_POINTS
            init_positions = initial_positions(walls, shape)
            bots[enemy_idx] = init_positions[enemy_idx]
            kills[turn] += 1
            deaths[enemy_idx] += 1
            bot_was_killed[enemy_idx] = True
            _logger.info(f"Bot {enemy_idx} reappears at {bots[enemy_idx]}.")
    else:
        # check if we have been eaten
        enemies_on_target = [idx for idx in enemy_idx if bots[idx] == bot_position]
        if len(enemies_on_target) > 0:
            _logger.info(f"Bot {turn} was eaten by bots {enemies_on_target} at {bot_position}.")
            score[1 - team] = score[1 - team] + KILL_POINTS
            init_positions = initial_positions(walls, shape)
            bots[turn] = init_positions[turn]
            deaths[turn] += 1
            kills[enemies_on_target[0]] += 1
            bot_was_killed[turn] = True
            _logger.info(f"Bot {turn} reappears at {bots[turn]}.")

    errors = gamestate["errors"]
    errors[team] = team_errors
    gamestate_new = {
        "food": food,
        "bots": bots,
        "score": score,
        "deaths": deaths,
        "kills": kills,
        "bot_was_killed": bot_was_killed,
        "errors": errors,
        }

    gamestate.update(gamestate_new)
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

    if game_state['gameover']:
        raise ValueError("Game is already over")
    turn = game_state['turn']
    round = game_state['round']

    if turn is None and round is None:
        turn = 0
        round = 1
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


def check_gameover(game_state, detect_final_move=False):
    """ Checks if this was the final moves or if the errors have exceeded the threshold.

    Returns
    -------
    dict { 'gameover' , 'whowins' }
        Flags if the game is over and who won it
    """

    # If any team has a fatal error, this team loses.
    # If both teams have a fatal error, it’s a draw.
    num_fatals = [len(f) for f in game_state['fatal_errors']]
    if num_fatals[0] == 0 and num_fatals[1] == 0:
        # no one has any fatal errors
        pass
    elif num_fatals[0] > 0 and num_fatals[1] > 0:
        # both teams have fatal errors: it is a draw
        return { 'whowins' : 2, 'gameover' : True}
    else:
        # some one has fatal errors
        for team in (0, 1):
            if num_fatals[team] > 0:
                return { 'whowins' : 1 - team, 'gameover' : True}

    # If any team has reached error_limit errors, this team loses.
    # If both teams have reached error_limit errors, it’s a draw.
    # If error_limit is 0, the game will go on without checking.
    num_errors = [len(f) for f in game_state['errors']]
    if game_state['error_limit'] == 0:
        pass
    elif num_errors[0] < game_state['error_limit'] and num_errors[1] < game_state['error_limit']:
        # no one has reached the error limit
        pass
    elif num_errors[0] >= game_state['error_limit'] and num_errors[1] >= game_state['error_limit']:
        # both teams have reached or exeeded the error limit
        return { 'whowins' : 2, 'gameover' : True}
    else:
        # only one team has reached the error limit
        for team in (0, 1):
            if num_errors[team] >= game_state['error_limit']:
                return { 'whowins' : 1 - team, 'gameover' : True}

    if detect_final_move:
        # No team wins/loses because of errors?
        # Good. Now check if the game finishes because the food is gone
        # or because we are in the final turn of the last round.

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
            return { 'whowins' : whowins, 'gameover' : True}

    return { 'whowins' : None, 'gameover' : False}


def check_exit_remote_teams(game_state):
    """ If the we are gameover, we want the remote teams to shut down. """
    if game_state['gameover']:
        _logger.info("Gameover. Telling teams to exit.")
        for idx, team in enumerate(game_state['teams']):
            if len(game_state['fatal_errors'][idx]) > 0:
                _logger.info(f"Not sending exit to team {idx} which had a fatal error.")
                # We pretend we already send the exit message, otherwise
                # the team’s __del__ method will do it once more.
                team._sent_exit = True
                continue
            try:
                team_game_state = prepare_bot_state(game_state, idx=idx)
                team._exit(team_game_state)
            except AttributeError:
                pass


def split_food(width, food):
    team_food = [set(), set()]
    for pos in food:
        idx = pos[0] // (width // 2)
        team_food[idx].add(pos)
    return team_food


def game_print(turn, msg):
    allow_unicode = not _mswindows
    if turn % 2 == 0:
        pie = ('\033[94m' + 'ᗧ' + '\033[0m' + ' ') if allow_unicode else ''
        pie += f'blue team, bot {turn // 2}'
    elif turn % 2 == 1:
        pie = ('\033[91m' + 'ᗧ' + '\033[0m' + ' ') if allow_unicode else ''
        pie += f'red team, bot {turn // 2}'
    print(f'{pie}: {msg}')
