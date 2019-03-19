"""This is the game module. Written in 2019 in Born by Carlos and Lisa."""

import dataclasses
import logging
from random import Random
import sys
import typing

from . import layout
from .gamestate_filters import noiser
from .player.team import make_team

_logger = logging.getLogger(__name__)

class FatalException(Exception): # TODO rename to FatalGameException etc
    pass

class NonFatalException(Exception):
    pass

class PlayerTimeout(NonFatalException):
    pass

class PlayerDisconnected(FatalException):
    # unsure, if PlayerDisconnected should be fatal in the sense of that the team loses
    # it could simply be a network error for both teams
    # and it would be random who will be punished
    pass

@dataclasses.dataclass
class GameState:
    """ Internal game state. """

    ### The layout attributes
    #: Walls. List of (int, int)
    walls: typing.List

    #: Food. List of (int, int)
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

    def pretty_str(self):
        return (layout.layout_as_str(walls=self.walls, food=self.food, bots=self.bots) + "\n" +
                str({ f.name: getattr(self, f.name) for f in dataclasses.fields(self) if f.name not in ['walls', 'food']}))

def run_game(team_specs, *, rounds, layout_dict, layout_name="", seed=None, dump=False,
             max_team_errors=5, timeout_length=3, viewers=None):

    if viewers is None:
        viewers = []

    # we create the initial game state
    # initialize the exceptions lists
    state = setup_game(team_specs, layout_dict, max_rounds=rounds, seed=seed)

    while not state.get('gameover'):
        state = play_turn(state)

        # generate the reduced viewer state
        viewer_state = prepare_viewer_state(state)
        for viewer in viewers:
            # show a state to the viewer
            viewer.show_state(state)

    return state

def setup_game(team_specs, layout_dict, max_rounds=300, seed=None):
    """ Generates a game state for the given teams and layout with otherwise default values. """
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
        food=layout_dict['food'][:],
        walls=layout_dict['walls'][:],
        deaths=[0] * 2,
        say=[""] * 2,
        layout_name=None,
        team_names=[None] * 2,
        fatal_errors=[False] * 2,
        errors=[[], []],
        whowins=None,
        rnd=Random(seed)
    )
    game_state = dataclasses.asdict(game_state)

    # we start with a dummy zmq_context
    # make_team will generate and return a new context, if it is needed
    zmq_context = None
    
    game_state['team_specs'] = []
    for idx, team_spec in enumerate(team_specs):
        team, zmq_context = make_team(team_spec)
        team_name = team.set_initial(idx, prepare_bot_state(game_state, idx))
        game_state['team_specs'].append(team)

    return game_state


def request_new_position(game_state):
    team = game_state['turn'] % 2
    bot_turn = game_state['turn'] // 2
    move_fun = game_state['team_specs'][team]

    bot_state = prepare_bot_state(game_state)
    new_position = move_fun.get_move(bot_state)
    return new_position

def prepare_bot_state(game_state, idx=None):
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
        'food': [food for food in game_state['food'] if in_homezone(food, own_team)]
    }

    enemy_state = {
        'team_index': enemy_team,
        'bot_positions': noised_positions['enemy_positions'],
        'is_noisy': noised_positions['is_noisy'],
        'score': game_state['score'][enemy_team],
        'timeout_count': 0, # TODO. Could be left out for the enemy
        'food': [food for food in game_state['food'] if in_homezone(food, enemy_team)]
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

def prepare_viewer_state(game_state):
    return game_state


def play_turn(game_state):
    # if the game is already over, we return a value error
    if game_state['gameover']:
        raise ValueError("Game is already over!")

    if game_state['round'] is None:
        # we have not started yet
        # initialize round and turn
        game_state['round'] = 0
        game_state['turn'] = 0

    if game_state['round'] >= game_state['max_rounds']:
        # TODO
        # set gameover state properly
        game_state['gameover'] = True
        return game_state

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
        # NoneFatalExceptions (such as Timeouts and ValueErrors in the JSON handling)
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
    if len(team_errors) > 4 or fatal_error:
        gameover = True
        whowins = 1 - team  # the other team
        new_turn = None
        new_round = None
    else:
        # take step
        bots[turn] = bot_position
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
            if bot_position in food:
                food.pop(food.index(bot_position))
                # This is modifying the old game state
                score[team] = score[team] + 1
        # check if anyone was eaten
        if bot_in_homezone:
            enemy_bots = [bots[i] for i in enemy_idx]
            if bot_position in enemy_bots:
                score[team] = score[team] + 5
                eaten_idx = enemy_idx[enemy_bots.index(bot_position)]
                init_positions = initial_positions(walls)
                bots[eaten_idx] = init_positions[eaten_idx]
                deaths[abs(team-1)] = deaths[abs(team-1)] + 1

        # check for game over
        whowins = None
        if n_round+1 >= gamestate["max_rounds"]:
            gameover = True
            if score[0] > score[1]:
                whowins = 0
            elif score[0] < score[1]:
                whowins = 1
            else:
                # tie
                whowins = 2
        new_turn = (turn + 1) % 4
        if new_turn == 0:
            new_round = n_round + 1
        else:
            new_round = n_round

    errors = gamestate["errors"]
    errors[team] = team_errors
    gamestate_new = {
        "food": food,
        "bots": bots,
        "turn": new_turn,
        "round": new_round,
        "gameover": gameover,
        "whowins": whowins,
        "score": score,
        "deaths": deaths,
        "errors": errors
        }

    gamestate.update(gamestate_new)
    return gamestate


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
