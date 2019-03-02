"""This is the game module. Written in 2019 in Born by Carlos and Lisa."""
from random import randint

def run_game(team_specs, *, rounds, layout_dict, layout_name="", seed=None, dump=False,
                            max_team_errors=5, timeout_length=3, viewers=None):

    if viewers is None:
        viewers = []

    # we create the initial game state
    # initialize the exceptions lists
    state = setup_game(team_specs, layout_dict)

    while not state.get('gameover'):
        state = play_turn_(state)

        for viewer in viewers:
            # show a state to the viewer
            viewer.show_state(state)

    return state

def setup_game(team_specs, layout_dict):
    game_state = {}
    game_state.update(layout_dict)

    # for now team_specs will be two move functions
    game_state['team_specs'] = []
    for team in team_specs:
        # wrap the move function in a Team
        from .player.team import Team as _Team
        team_player = _Team('local-team', team)
        game_state['team_specs'].append(team_player)

    return game_state

def request_new_position(game_state):
    team = game_state['turn'] % 2
    move_fun = game_state['team_specs'][team]

    bot_state = prepare_bot_state(game_state)
    return move_fun(bot_state)

def play_turn_(game_state):
    # if the game is already over, we return a value error
    if game_state['gameover']:
        raise ValueError("Game is already over!")

    team = game_state['turn'] % 2
    # request a new move from the current team
    try:
        position = request_new_position(game_state)
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
    game_state = play_turn(game_state, position)
    return game_state


def play_turn(gamestate, bot_position):
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

    # previous errors
    team_errors = gamestate["errors"][team]
    # check is step is legal

    legal_moves = get_legal_moves(walls, gamestate["bots"][gamestate["turn"]])
    if bot_position not in legal_moves:
        bot_position = legal_moves[randint(0, len(legal_moves)-1)]
        error_dict = {
            "turn": turn,
            "round": n_round,
            "reason": 'illegal move',
            "bot_position": bot_position
            }
        team_errors.append(error_dict)
        new_turn = None
        new_round = None
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
        if n_round+1 >= gamestate["max_round"]:
            gameover = True
            if score[0] > score[1]:
                whowins = 0
            elif score[0] < score[1]:
                whowins = 1
            else:
                # tie
                whowins = 2
        if gamestate["timeout"]:
            gameover = True
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


#  canonical_keys = {
#                  "food" food,
#                  "walls": walls,
#                  "bots": bots,
#                  "maxrounds": maxrounds,
#                  "team_names": team_names,
#                  "turn": turn,
#                  "round": round,
#                  "timeouts": timeouts,
#                  "gameover": gameover,
#                  "whowins": whowins,
#                  "team_say": team_say,
#                  "score": score,
#                  "deaths": deaths,
#                  }

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
# - write tests for play turn (check that all rules are correctly applied)
# - refactor Rike's initial positions code
# - keep track of error dict for future additions