"""This is the game module. Written in 2019 in Born by Carlos and Lisa."""
from random import randint

def play_turn(gamestate, bot_position):
    """Plays a single step of a bot.

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
    # decide which team
    team = turn % 2
    enemy_idx = (1, 3) if team == 0 else(0, 2)

    gameover = gamestate["gameover"]
    score = gamestate["score"]
    food = gamestate["food"]
    walls = gamestate["walls"]
    food = gamestate["food"]
    round = gamestate["round"]
    deaths = gamestate["deaths"]
    fatal_error = True if gamestate["fatal_errors"][team] else False

    # previous errors
    team_errors = gamestate["errors"][team]
    # check is step is legal
    legal_moves = get_legal_moves(walls, bot_position)
    if bot_position not in legal_moves:
        bot_position = legal_moves[randint(0, 4)]
        error_dict = {
            "turn": turn,
            "round": round,
            "reason": 'illegal move',
            "bot_position": bot_position
            }
        team_errors.append(error_dict)
    # only execute move if errors not exceeded
    if len(team_errors) > 4 or fatal_error:
        gameover = True
        whowins = 1-team # the other team
    else:
        # take step
        bots[turn] = bot_position
        # then apply rules
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
                score[team] = score[team] + 1


        # check if anyone was eaten
        if bot_in_homezone:
            enemy_bots = [bots[i] for i in enemy_idx]
            if bot_position in enemy_bots:
                score[team] = score[team] + 5
                eaten_idx = enemy_idx[enemy_bots.index(bot_position)]
                init_positions = initial_positions(walls)
                bots[eaten_idx] = init_positions[eaten_idx]
                deaths[team] = deaths[team] + 1

        # check for game over
        whowins = None
        if round+1 >= gamestate["max_round"]:
            gameover = True
            whowins = 0 if score[0] > score[1] else 1
        if gamestate["timeout"]:
            gameover = True
        new_turn = (turn + 1) % 4
        if new_turn == 0:
            new_round = round + 1
        else:
            new_round = round

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