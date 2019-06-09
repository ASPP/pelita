"""This is the game module. Written in 2019 in Born by Carlos and Lisa."""

import dataclasses
import itertools
import logging
import os
from random import Random
import subprocess
import sys
import typing
from warnings import warn

from . import layout
from .exceptions import FatalException, NonFatalException, NoFoodWarning
from .gamestate_filters import noiser
from .layout import initial_positions, get_legal_moves
from .libpelita import get_python_process, SimplePublisher
from .network import bind_socket, setup_controller
from .player.team import make_team
from .viewer import ProgressViewer, AsciiViewer, ReplyToViewer, DumpingViewer, ResultPrinter

_logger = logging.getLogger(__name__)
_mswindows = (sys.platform == "win32")


### Global constants
# All constants that are currently not redefinable in setup_game

#: Maximum number of errors before a team loses
MAX_ALLOWED_ERRORS = 4

#: The maximum distance between two bots before noise is applied
SIGHT_DISTANCE = 5

#: The radius for the uniform noise
NOISE_RADIUS = 5

@dataclasses.dataclass
class GameState:
    """ Internal game state. """

    ### The layout attributes
    #: Walls. List of (int, int)
    walls: typing.List

    #: Food per team. List of sets of (int, int)
    food: typing.List

    def width(self):
        """ The width of the maze. """
        return max(self.walls)[0]

    def height(self):
        """ The height of the maze. """
        return max(self.walls)[1]

    ### Round/turn information
    #: Current bot
    turn: int

    def current_team(self):
        """ The team of the current turn. """
        return self.turn % 2

    #: Current round
    round: int

    #: Is the game finished?
    gameover: bool

    #: Who won?
    whowins: int

    ### Bot/team status
    #: Positions of all bots. List of (int, int)
    bots: typing.List

    #: Score of the teams. List of int
    score: typing.List[int]

    #: Death (respawn) count of the teams. List of int
    deaths: typing.List[int]

    #: Fatal errors
    fatal_errors: typing.List

    #: Errors
    errors: typing.List

    ### Configuration
    #: Maximum number of rounds
    max_rounds: int

    #: Time till timeout
    timeout: int

    #: Noise radius
    noise_radius: int

    #: Sight distance
    sight_distance: int

    ### Informative
    #: Name of the layout
    layout_name: str

    #: Name of the teams. List of str
    team_names: typing.List[str]

    #: Time each team needed
    team_time: typing.List[float]

    #: Times each team got killed
    times_killed: typing.List[int]

    #: Recently respawned?
    respawned: typing.List[int]

    #: Messages the bots say. Keeps only the recent one at the respective bot’s index.
    say: typing.List[str]

    ### Internal
    #: Internal team representation
    teams: typing.List

    #: Random number generator
    rnd: typing.Any

    #: Viewers
    viewers: typing.List

    #: Controller
    controller: typing.Optional

    def pretty_str(self):
        return (layout.layout_as_str(walls=self.walls, food=list(self.food[0] | self.food[1]), bots=self.bots) + "\n" +
                str({ f.name: getattr(self, f.name) for f in dataclasses.fields(self) if f.name not in ['walls', 'food']}))


class TkViewer:
    def __init__(self, *, address, controller, geometry=None, delay=None, stop_after=None):
        self.proc = self._run_external_viewer(address, controller, geometry=geometry, delay=delay, stop_after=stop_after)

    def _run_external_viewer(self, subscribe_sock, controller, geometry, delay, stop_after):
        # Something on OS X prevents Tk from running in a forked process.
        # Therefore we cannot use multiprocessing here. subprocess works, though.
        viewer_args = [ str(subscribe_sock) ]
        if controller:
            viewer_args += ["--controller-address", str(controller)]
        if geometry:
            viewer_args += ["--geometry", "{0}x{1}".format(*geometry)]
        if delay:
            viewer_args += ["--delay", str(delay)]
        if stop_after is not None:
            viewer_args += ["--stop-after", str(stop_after)]

        tkviewer = 'pelita.scripts.pelita_tkviewer'
        external_call = [get_python_process(),
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

def run_game(team_specs, *, max_rounds, layout_dict, layout_name="", seed=None, dump=False,
             max_team_errors=5, timeout_length=3, viewers=None, controller=None, viewer_options=None):
    """ Run a match for `max_rounds` rounds. """

    # we create the initial game state
    state = setup_game(team_specs, layout_dict=layout_dict, max_rounds=max_rounds, seed=seed,
                       viewers=viewers, controller=controller, viewer_options=viewer_options)

    # Play the game until it is gameover.
    while not state.get('gameover'):

        # this is only needed if we have a controller, for example a viewer
        # this function call *blocks* until the viewer has replied
        if controller_exit(state):
            # if the controller asks us, we'll exit and stop playing
            break

        # play the next turn
        state = play_turn(state)

    return state


def setup_viewers(viewers=None, options=None):
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
        elif len(viewer) == 2 and viewer[0] == 'dump-to':
            viewer_state['viewers'].append(DumpingViewer(open(viewer[1], 'w')))
        elif viewer in ('tk', 'tk-no-sync'):
            if not zmq_publisher:
                zmq_publisher = SimplePublisher(address='tcp://127.0.0.1:*')
                viewer_state['viewers'].append(zmq_publisher)
            if viewer == 'tk':
                viewer_state['controller'] = setup_controller()
            if viewer_state['controller']:
                proc = TkViewer(address=zmq_publisher.socket_addr, controller=viewer_state['controller'].socket_addr,
                                stop_after=options.get('stop_at'),
                                geometry=options.get('geometry'),
                                delay=options.get('delay'))
            else:
                proc = TkViewer(address=zmq_publisher.socket_addr, controller=None,
                                stop_after=options.get('stop_at'),
                                geometry=options.get('geometry'),
                                delay=options.get('delay'))

        else:
            raise ValueError(f"Unknown viewer {viewer}.")

    # Add the result printer as the final viewer:
    viewer_state['viewers'].append(ResultPrinter())

    return viewer_state


def setup_game(team_specs, *, layout_dict, max_rounds=300, layout_name="", seed=None, dump=False,
               max_team_errors=5, timeout_length=3, viewers=None, controller=None, viewer_options=None):
    """ Generates a game state for the given teams and layout with otherwise default values. """

    # check that two teams have been given
    if not len(team_specs) == 2:
        raise ValueError("Two teams must be given.")
    
    # check that the given bot positions are all valid
    if not len(layout_dict['bots']) == 4:
        raise ValueError("Number of bots in layout must be 4.")
    
    width, height = layout.wall_dimensions(layout_dict['walls'])

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

    def split_food(width, food):
        team_food = [set(), set()]
        for pos in food:
            idx = pos[0] // (width // 2)
            team_food[idx].add(pos)
        return team_food

    food = split_food(width, layout_dict['food'])

    # warn if one of the food lists is already empty
    side_no_food = [idx for idx, f in enumerate(food) if len(f) == 0]
    if side_no_food:
        warn(f"Layout has no food for team {side_no_food}.", NoFoodWarning)
    
    viewer_state = setup_viewers(viewers, options=viewer_options)

    game_state = GameState(
        teams=[None] * 2,
        bots=layout_dict['bots'][:],
        turn=None,
        round=None,
        max_rounds=max_rounds,
        timeout=3,
        noise_radius=NOISE_RADIUS,
        sight_distance=SIGHT_DISTANCE,
        gameover=False,
        score=[0] * 2,
        food=food,
        walls=layout_dict['walls'][:],
        deaths=[0] * 2,
        say=[""] * 4,
        layout_name=None,
        team_names=[None] * 2,
        fatal_errors=[[], []],
        errors=[[], []],
        whowins=None,
        rnd=Random(seed),
        viewers=[],
        controller=None,
        team_time=[0, 0],
        times_killed=[0, 0],
        respawned=[True] * 4
    )
    game_state = dataclasses.asdict(game_state)

    # We must set the viewers after `asdict` to avoid
    # deepcopying the zmq sockets
    game_state['viewers'] = viewer_state['viewers']
    game_state['controller'] = viewer_state['controller']

    # Wait until the controller tells us that it is ready
    # We then can send the initial maze
    # This call *blocks* until the controller replies
    if controller_exit(game_state, await_action='set_initial'):
        return game_state

    # Send maze before team creation.
    # This gives a more fluent UI as it does not have to wait for the clients
    # to answer to the server.
    update_viewers(game_state)

    team_state = setup_teams(team_specs, game_state)
    game_state.update(team_state)

    # Check if one of the teams has already generate a fatal error
    # or if the game has finished (might happen if we set it up with max_rounds=0).
    game_state.update(check_gameover(game_state, detect_final_move=True))

    # Send updated game state with team names to the viewers
    update_viewers(game_state)

    return game_state


def setup_teams(team_specs, game_state):
    """ Creates the teams according to the `teams`. """

    # we start with a dummy zmq_context
    # make_team will generate and return a new context, if it is needed
    zmq_context = None

    teams = []
    # First, create all teams
    # If a team is a RemoteTeam, this will start a subprocess
    for idx, team_spec in enumerate(team_specs):
        team, zmq_context = make_team(team_spec, idx=idx)
        teams.append(team)

    # Send the initial state to the teams and await the team name
    team_names = []
    for idx, team in enumerate(teams):
        try:
            team_name = team.set_initial(idx, prepare_bot_state(game_state, idx))
        except FatalException as e:
            exception_event = {
                'type': e.__class__.__name__,
                'description': str(e),
                'turn': idx,
                'round': None,
            }
            game_state['fatal_errors'][idx].append(exception_event)
            position = None
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
    new_position = move_fun.get_move(bot_state)
    return new_position


def prepare_bot_state(game_state, idx=None):
    """ Prepares the bot’s game state for the current bot.

    """

    if game_state.get('turn') is None and idx is not None:
        # We assume that we are in get_initial phase
        turn = idx
        bot_turn = None
        seed = game_state['rnd'].randint(0, sys.maxsize)
    else:
        turn = game_state['turn']
        bot_turn = game_state['turn'] // 2
        seed = None

    bot_position = game_state['bots'][turn]
    own_team = turn % 2
    enemy_team = 1 - own_team
    enemy_positions = game_state['bots'][enemy_team::2]
    noised_positions = noiser(walls=game_state['walls'],
                              bot_position=bot_position,
                              enemy_positions=enemy_positions,
                              noise_radius=game_state['noise_radius'],
                              sight_distance=game_state['sight_distance'],
                              rnd=game_state['rnd'])

    width = max(game_state['walls'])[0]
    def in_homezone(position, team_id):
        on_left_side = position[0] < width // 2
        if team_id % 2 == 0:
            return on_left_side
        else:
            return not on_left_side

    respawned = game_state['respawned'][own_team::2]
    # reset the respawned cache
    game_state['respawned'][own_team::2] = [False, False]

    team_state = {
        'team_index': own_team,
        'bot_positions': game_state['bots'][own_team::2],
        'score': game_state['score'][own_team],
        'has_respawned': respawned,
        'timeout_count': len(game_state['errors'][own_team]),
        'food': list(game_state['food'][own_team]),
        'name': game_state['team_names'][own_team]
    }

    enemy_state = {
        'team_index': enemy_team,
        'bot_positions': noised_positions['enemy_positions'],
        'is_noisy': noised_positions['is_noisy'],
        'score': game_state['score'][enemy_team],
        'timeout_count': 0, # TODO. Could be left out for the enemy
        'food': list(game_state['food'][enemy_team]),
        'name': game_state['team_names'][enemy_team]
    }

    bot_state = {
        'walls': game_state['walls'], # only in initial round
        'seed': seed, # only used in set_intital phase
        'team': team_state,
        'enemy': enemy_state,
        'round': game_state['round'],
        'bot_turn': bot_turn
    }

    return bot_state


def update_viewers(game_state):
    """ Sends the current game_state to the viewers. """
    viewer_state = prepare_viewer_state(game_state)
    for viewer in game_state['viewers']:
        viewer.show_state(viewer_state)


def prepare_viewer_state(game_state):
    """ Prepares a state that can be sent to the viewers. """
    viewer_state = {}
    viewer_state.update(game_state)
    viewer_state['food'] = list((viewer_state['food'][0] | viewer_state['food'][1]))
    del viewer_state['teams']
    del viewer_state['rnd']
    del viewer_state['viewers']
    del viewer_state['controller']
    return viewer_state


def play_turn(game_state):
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
    game_state.update(update_round_counter(game_state))

    turn = game_state['turn']
    team = turn % 2
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
        # NonFatalExceptions (such as Timeouts and ValueErrors in the JSON handling)
        # are collected and added to team_errors
        exception_event = {
            'type': e.__class__.__name__,
            'description': str(e),
            'turn': game_state['turn'],
            'round': game_state['round'],
        }
        game_state['errors'][team].append(exception_event)
        position = None
        game_print(turn, f"{type(e).__name__}: {e}")

    # Check if a team has exceeded their maximum number of errors
    # (we do not want to apply the move in this case)
    # Note: Since we already updated the move counter, we do not check anymore,
    # if the game has exceeded its rounds.
    game_state.update(check_gameover(game_state))

    if not game_state['gameover']:
        # ok. we can apply the move for this team
        # try to execute the move and return the new state
        game_state = apply_move(game_state, position)

        # Check again, if we had errors or if this was the last move of the game (final round or food eaten)
        game_state.update(check_gameover(game_state, detect_final_move=True))

    # Send updated game state with team names to the viewers
    update_viewers(game_state)

    return game_state


def apply_move(gamestate, bot_position):
    """Plays a single step of a bot by applying the game rules to the game state. The rules are:
    - if the playing team has an error count of >5 or a fatal error they lose
    - a legal step must not be on a wall, else the error count is increased by 1 and a random move is chosen for the bot
    - if a bot lands on an enemy food pellet, it eats it. It cannot eat it's own teams food
    - if a bot lands on an enemy bot in it's own homezone, it kills the enemy
    - if a bot lands on an enemy bot in it's the enemy's homezone, it dies
    - when a bot dies, it respawns in it's own homezone
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
    food = gamestate["food"]
    n_round = gamestate["round"]
    deaths = gamestate["deaths"]
    fatal_error = True if gamestate["fatal_errors"][team] else False
    #TODO how are fatal errors passed to us? dict with same structure as regular errors?
    #TODO do we need to communicate that fatal error was the reason for game over in any other way?

    # previous errors
    team_errors = gamestate["errors"][team]
    # check is step is legal
    legal_moves = get_legal_moves(walls, gamestate["bots"][gamestate["turn"]])
    if bot_position not in legal_moves:
        bad_bot_position = bot_position
        bot_position = legal_moves[gamestate['rnd'].randint(0, len(legal_moves)-1)]
        error_dict = {
            "turn": turn,
            "round": n_round,
            "reason": 'illegal move',
            "bot_position": bot_position
            }
        game_print(turn, f"Illegal move {bad_bot_position} not in {sorted(legal_moves)}. Choosing a random move instead: {bot_position}")
        team_errors.append(error_dict)

    # only execute move if errors not exceeded
    gamestate.update(check_gameover(gamestate))
    if gamestate['gameover']:
        return gamestate

    # take step
    bots[turn] = bot_position
    _logger.info(f"Bot {turn} moves to {bot_position}.")
    # then apply rules
    # is bot in home or enemy territory
    x_walls = [i[0] for i in walls]
    boundary = max(x_walls) / 2  # float
    if team == 0:
        bot_in_homezone = bot_position[0] < boundary
    elif team == 1:
        bot_in_homezone = bot_position[0] > boundary
    # update food list
    if not bot_in_homezone:
        if bot_position in food[1 - team]:
            _logger.info(f"Bot {turn} eats food at {bot_position}.")
            food[1 - team].remove(bot_position)
            # This is modifying the old game state
            score[team] = score[team] + 1
    # check if anyone was eaten
    if bot_in_homezone:
        killed_enemies = [idx for idx in enemy_idx if bot_position == bots[idx]]
        for enemy_idx in killed_enemies:
            _logger.info(f"Bot {turn} eats enemy bot {enemy_idx} at {bot_position}.")
            score[team] = score[team] + 5
            init_positions = initial_positions(walls)
            bots[enemy_idx] = init_positions[enemy_idx]
            gamestate['respawned'][enemy_idx] = True
            deaths[abs(team-1)] = deaths[abs(team-1)] + 1
            _logger.info(f"Bot {enemy_idx} respawns at {bots[enemy_idx]}.")
    else:
        # check if bot was eaten itself
        enemies_on_target = [idx for idx in enemy_idx if bots[idx] == bot_position]
        if len(enemies_on_target) > 0:
            _logger.info(f"Bot {turn} was eaten by bots {enemies_on_target} at {bot_position}.")
            score[1 - team] = score[1 - team] + 5
            init_positions = initial_positions(walls)
            bots[turn] = init_positions[turn]
            gamestate['respawned'][turn] = True
            deaths[team] = deaths[team] + 1
            _logger.info(f"Bot {turn} respawns at {bots[turn]}.")

    errors = gamestate["errors"]
    errors[team] = team_errors
    gamestate_new = {
        "food": food,
        "bots": bots,
        "score": score,
        "deaths": deaths,
        "errors": errors
        }

    gamestate.update(gamestate_new)
    return gamestate


def update_round_counter(game_state):
    """ Takes the round and turn from the game state dict, increases them by one
    and returns a new dict.

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

#    if round >= game_state['max_rounds']:
#        raise ValueError("Exceeded maximum number of rounds.")

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

    # If any team has more than MAX_ALLOWED_ERRORS errors, this team loses.
    # If both teams have more than MAX_ALLOWED_ERRORS errors, it’s a draw.
    num_errors = [len(f) for f in game_state['errors']]
    if num_errors[0] <= MAX_ALLOWED_ERRORS and num_errors[1] <= MAX_ALLOWED_ERRORS:
        # no one has exceeded the max number of errors
        pass
    elif num_errors[0] > MAX_ALLOWED_ERRORS and num_errors[1] > MAX_ALLOWED_ERRORS:
        # both teams have exceeded the max number of errors
        return { 'whowins' : 2, 'gameover' : True}
    else:
        # some one has exceeded the max number of errors
        for team in (0, 1):
            if num_errors[team] > MAX_ALLOWED_ERRORS:
                return { 'whowins' : 1 - team, 'gameover' : True}

    if detect_final_move:
        # No team wins/loses because of errors?
        # Good. Now check if the game finishes because the food is gone
        # or because we are in the final turn of the last round.
        next_step = update_round_counter(game_state)
        _logger.debug(f"Next step has {next_step}")

        # count how much food is left for each team
        food_left = [len(f) for f in game_state['food']]
        if next_step['round'] > game_state['max_rounds'] or any(f == 0 for f in food_left):
            if game_state['score'][0] > game_state['score'][1]:
                whowins = 0
            elif game_state['score'][0] < game_state['score'][1]:
                whowins = 1
            else:
                whowins = 2
            return { 'whowins' : whowins, 'gameover' : True}

    return { 'whowins' : None, 'gameover' : False}


# TODO ???
# - refactor Rike's initial positions code
# - keep track of error dict for future additions

def game_print(turn, msg):
    if turn % 2 == 0:
        pie = '\033[94m' + 'ᗧ' + '\033[0m' + f' blue team, bot {turn // 2}'
    elif turn % 2 == 1:
        pie = '\033[91m' + 'ᗧ' + '\033[0m' + f' red team, bot {turn // 2}'
    print(f'{pie}: {msg}')
