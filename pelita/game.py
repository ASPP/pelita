"""This is the game module. Written in 2019 in Born by Carlos and Lisa."""

import dataclasses
import itertools
import logging
import os
from random import Random
import subprocess
import sys
import typing

from . import layout
from .exceptions import FatalException, NonFatalException
from .gamestate_filters import noiser
from .libpelita import get_python_process, SimplePublisher
from .network import bind_socket, setup_controller
from .player.team import make_team
from .viewer import ProgressViewer

_logger = logging.getLogger(__name__)
_mswindows = (sys.platform == "win32")

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

    #: Messages the bots say. Keeps only the recent one at the respective bot’s index.
    say: typing.List[str]

    ### Internal
    #: Internal team representation
    team_specs: typing.List

    #: Random number generator
    rnd: typing.Any

    #: Viewers
    viewers: typing.List

    #: Controller
    controller: typing.Optional

    def pretty_str(self):
        return (layout.layout_as_str(walls=self.walls, food=self.food, bots=self.bots) + "\n" +
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


def run_game(team_specs, *, max_rounds, layout_dict, layout_name="", seed=None, dump=False,
             max_team_errors=5, timeout_length=3, viewers=None, controller=None, viewer_options=None):
    """ Run a match for `max_rounds` rounds. """

    if viewers is None:
        viewers = []

    # we create the initial game state
    state = setup_game(team_specs, layout_dict=layout_dict, max_rounds=max_rounds, seed=seed,
                       viewers=viewers, controller=controller, viewer_options=viewer_options)

    # Play the game until it is gameover.
    while not state.get('gameover'):

        # If we have a controller, wait here for a `play_step` message.
        if state['controller']:
            action = state['controller'].await_action('play_step')
            if action == 'exit':
                break
            elif action == 'play_step':
                pass

        state = play_turn(state)

    # The game is over. We are nice and clean up.
    # for team in state['team_specs']:
    #    if hasattr(team, '_exit'):
    #        team._exit()

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
            pass
        elif viewer == 'progress':
            viewer_state['viewers'].append(ProgressViewer())
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

    return viewer_state


def setup_game(team_specs, *, layout_dict, max_rounds=300, layout_name="", seed=None, dump=False,
               max_team_errors=5, timeout_length=3, viewers=None, controller=None, viewer_options=None):
    """ Generates a game state for the given teams and layout with otherwise default values. """
    def split_food(width, food):
        team_food = [set(), set()]
        for pos in food:
            idx = pos[0] // (width // 2)
            team_food[idx].add(pos)
        return team_food

    viewer_state = setup_viewers(viewers, options=viewer_options)
    
    width = max(layout_dict['walls'])[0] + 1
    food = split_food(width, layout_dict['food'])

    game_state = GameState(
        team_specs=[None] * 2,
        bots=layout_dict['bots'][:],
        turn=None,
        round=None,
        max_rounds=max_rounds,
        timeout=3,
        noise_radius=5,
        sight_distance=5,
        gameover=False,
        score=[0] * 2,
        food=food,
        walls=layout_dict['walls'][:],
        deaths=[0] * 2,
        say=[""] * 4,
        layout_name=None,
        team_names=[None] * 2,
        fatal_errors=[False] * 2,
        errors=[[], []],
        whowins=None,
        rnd=Random(seed),
        viewers=[],
        controller=None,
    )
    game_state = dataclasses.asdict(game_state)

    # We must set the viewers after `asdict` to avoid
    # deepcopying the zmq sockets
    game_state['viewers'] = viewer_state['viewers']
    game_state['controller'] = viewer_state['controller']

    if game_state['controller']:
        # Wait until the controller tells us that it is ready
        # We then can send the initial maze
        # TODO: Waiting for the viewer to be ready could
        # be done simultaneously with calling setup_teams
        action = game_state['controller'].await_action('set_initial')
        if action == 'exit':
            return game_state
        elif action == 'set_initial':
            pass

    # Send maze before team creation.
    # This gives a more fluent UI as it does not have to wait for the clients
    # to answer to the server.
    update_viewers(game_state)

    team_state = setup_teams(team_specs, game_state)
    game_state.update(team_state)

    # Send updated game state with team names to the viewers
    update_viewers(game_state)

    return game_state


def setup_teams(team_specs, game_state):
    """ Creates the teams according to the `team_specs`. """
    team_state = {
        'team_specs': [],
        'team_names': []
    }

    # we start with a dummy zmq_context
    # make_team will generate and return a new context, if it is needed
    zmq_context = None

    for idx, team_spec in enumerate(team_specs):
        team, zmq_context = make_team(team_spec, idx=idx)
        team_name = team.set_initial(idx, prepare_bot_state(game_state, idx))
        team_state['team_names'].append(team_name) # TODO this could be an attribute of the team_spec team (and only be used in prepare_viewer).
        team_state['team_specs'].append(team)
    
    return team_state


def request_new_position(game_state):
    team = game_state['turn'] % 2
    bot_turn = game_state['turn'] // 2
    move_fun = game_state['team_specs'][team]

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

    team_state = {
        'team_index': own_team,
        'bot_positions': game_state['bots'][own_team::2],
        'score': game_state['score'][own_team],
        'has_respawned': [False] * 2, # TODO
        'timeout_count': 0, # TODO
        'food': list(game_state['food'][own_team]), #[food for food in game_state['food'] if in_homezone(food, own_team)]
    }

    enemy_state = {
        'team_index': enemy_team,
        'bot_positions': noised_positions['enemy_positions'],
        'is_noisy': noised_positions['is_noisy'],
        'score': game_state['score'][enemy_team],
        'timeout_count': 0, # TODO. Could be left out for the enemy
        'food': list(game_state['food'][enemy_team]), # [food for food in game_state['food'] if in_homezone(food, enemy_team)]
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
    del viewer_state['team_specs']
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

    # Check if the game is already finished (but gameover had not been set)
    # TODO maybe also check for errors here
    game_state.update(check_final_move(game_state))
    if game_state['gameover']:
        return game_state

    # Now update the round counter
    game_state.update(update_round_counter(game_state))

    team = game_state['turn'] % 2
    # request a new move from the current team
    try:
        position_dict = request_new_position(game_state)
        position = tuple(position_dict['move'])
        if position_dict.get('say'):
            game_state['say'][game_state['turn']] = position_dict['say']
    except FatalException as e:
        # FatalExceptions (such as PlayerDisconnect) should immediately
        # finish the game
        exception_event = {
            'type': str(e),
            'turn': game_state['turn'],
            'round': game_state['round'],
        }
        game_state['fatal_errors'][team].append(exception_event)
        position = None
    except NonFatalException as e:
        # NonFatalExceptions (such as Timeouts and ValueErrors in the JSON handling)
        # are collected and added to team_errors
        exception_event = {
            'type': str(e),
            'turn': game_state['turn'],
            'round': game_state['round'],
        }
        game_state['errors'][team].append(exception_event)
        position = None

    # try to execute the move and return the new state
    game_state = apply_move(game_state, position)

    # Check if this was the last move of the game (final round or food eaten)
    game_state.update(check_final_move(game_state))

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
        bot_position = legal_moves[gamestate['rnd'].randint(0, len(legal_moves)-1)]
        error_dict = {
            "turn": turn,
            "round": n_round,
            "reason": 'illegal move',
            "bot_position": bot_position
            }
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
            deaths[team] = deaths[team] + 1
            _logger.info(f"Bot {turn} respawns at {bots[turn]}.")

    gamestate.update(check_gameover(gamestate))

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
        round = 0
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
        'turn': turn,
        'round': round
    }


def check_gameover(game_state):
    """ Checks for errors and fatal errors in `game_state` and sets the winner
    accordingly.

    Returns
    -------
    dict { 'gameover' , 'whowins' }
        Flags if the game is over and who won it

    """

    # check for game over
    whowins = None
    gameover = False

    for team in (0, 1):
        if len(game_state['errors'][team]) > 4 or game_state['fatal_errors'][team]:
            gameover = True
            whowins = 1 - team  # the other team
            break

    return {
        'whowins': whowins,
        'gameover': gameover
    }


def check_final_move(game_state):
    """ Checks if this was the final move in the game or
    if one team has lost all their food.

    Returns
    -------
    dict { 'gameover' , 'whowins' }
        Flags if the game is over and who won it
    """

    if game_state['gameover']:
        # Game already finished.
        whowins = game_state['whowins']
        gameover = game_state['gameover']

    else:
        whowins = None
        gameover = False

        # The game is over when the next step would give us
        # game_state['round'] == game_state['max_rounds']
        # or when one team has lost all their food

        next_step = update_round_counter(game_state)
        _logger.debug(f"Next step has {next_step}")

        if next_step['round'] >= game_state['max_rounds'] or any(not f for f in game_state['food']):
            gameover = True
            if game_state['score'][0] > game_state['score'][1]:
                whowins = 0
            elif game_state['score'][0] < game_state['score'][1]:
                whowins = 1
            else:
                # tie
                whowins = 2

    return {
        'whowins': whowins,
        'gameover': gameover
    }


def initial_positions(walls):
    """Calculate initial positions.

    Given the list of walls, returns the free positions that are closest to the
    bottom left and top right corner. The algorithm starts searching from
    (1, height-2) and (width-2, 1) respectively and uses the Manhattan distance
    for judging what is closest. On equal distances, a smaller distance in the
    x value is preferred.
    """
    width = max(walls)[0] + 1
    height = max(walls)[1] + 1

    left_start = (1, height - 2)
    left = []
    right_start = (width - 2, 1)
    right = []

    dist = 0
    while len(left) < 2:
        # iterate through all possible x distances (inclusive)
        for x_dist in range(dist + 1):
            y_dist = dist - x_dist
            pos = (left_start[0] + x_dist, left_start[1] - y_dist)
            # if both coordinates are out of bounds, we stop
            if not (0 <= pos[0] < width) and not (0 <= pos[1] < height):
                raise ValueError("Not enough free initial positions.")
            # if one coordinate is out of bounds, we just continue
            if not (0 <= pos[0] < width) or not (0 <= pos[1] < height):
                continue
            # check if the new value is free
            if pos not in walls:
                left.append(pos)

            if len(left) == 2:
                break

        dist += 1

    dist = 0
    while len(right) < 2:
        # iterate through all possible x distances (inclusive)
        for x_dist in range(dist + 1):
            y_dist = dist - x_dist
            pos = (right_start[0] - x_dist, right_start[1] + y_dist)
            # if both coordinates are out of bounds, we stop
            if not (0 <= pos[0] < width) and not (0 <= pos[1] < height):
                raise ValueError("Not enough free initial positions.")
            # if one coordinate is out of bounds, we just continue
            if not (0 <= pos[0] < width) or not (0 <= pos[1] < height):
                continue
            # check if the new value is free
            if pos not in walls:
                right.append(pos)

            if len(right) == 2:
                break

        dist += 1

    # lower indices start further away
    left.reverse()
    right.reverse()
    return [left[0], right[0], left[1], right[1]]


def get_legal_moves(walls, bot_position):
    """ Returns legal moves given a position.

     Parameters
    ----------
    walls : list
        position of the walls of current layout.
    bot_position: tuple
        position of current bot.

    Returns
    -------
    list
        legal moves.
    """
    north = (0, -1)
    south = (0, 1)
    east = (1, 0)
    west = (-1, 0)
    stop = (0, 0)
    directions = [north, east, west, south, stop]
    potential_moves = [(i[0] + bot_position[0], i[1] + bot_position[1]) for i in directions]
    possible_moves = [i for i in potential_moves if i not in walls]
    return possible_moves

# TODO ???
# - refactor Rike's initial positions code
# - keep track of error dict for future additions
