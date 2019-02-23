"""This is the game module. Written in 2019 in Born by Carlos and Lisa."""


def play_turn(gamestate, turn, bot_position):
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
    # bots 0 and 2 are team 0
    # bots 1 and 3 are team 1
    # update bot positions
    bots = gamestate["bots"]
    bots[turn] = bot_position

    if (turn == 0 or turn == 2):
        team = 0
        enemy_idx = (1, 3)
    else:
        team = 1
        enemy_idx = (0, 2)
    x_walls = [i[0] for i in gamestate["walls"]]
    boundary = max(x_walls)/2  # float
    if team == 0:
        bot_in_homezone = bot_position[0] < boundary
    elif team == 1:
        bot_in_homezone = bot_position[0] > boundary

    # update food list
    if not bot_in_homezone:
        food_list = gamestate_old["food"]
        if bot_position in food_list:
            food_list.pop(food_list.index(bot_position))
            score[team] = score[team] + 1

    # check if anyone was eaten
    deaths = gamestate["deaths"]
    if bot_in_homezone:
        enemy_bots = [bots[i] for i in enemy_idx]
        if bot_position in enemy_bots:
            score[team] = score[team] + 5
            eaten_idx = enemy_idx[enemy_bots.index(bot_position)]
            init_positions = initial_positions(gamestate["walls"])
            bots[eaten_idx] = init_positions[eaten_idx]
            deaths[team] = deaths[team] + 1

    # check for game over
    gameover = gamestate["gameover"]
    whowins = None
    if gamestate["round"]+1 >= gamestate["max_round"]:
        gameover = True
        whowins = 0 if score[0] > score[1] else 1
    new_turn = (turn + 1) % 4
    gamestate = {
                 "turn": new_turn,
                 "round": gamestate_old["round"] + 1,
                 "max_round": gamestate_old["max_round"],
                 "walls": gamestate_old["walls"],
                 "food": gamestate_old["food"],
                 "bots": bots,
                 "timeouts": gamestate_old["timeouts"],
                 "gameover": gameover,
                 "whowins": whowins,
                 "team_names": gamestate_old["team_names"],
                 "team_say": 'pos!!',
                 "score": score,
                 "deaths": deaths
    }

    return gamestate

def get_initial_positions(walls):
    """ Returns the free positions that are closest to the bottom left and
    top right corner. The algorithm starts searching from (1, height-2) and
    (width-2, 1) respectively and uses the manhattan distance for judging what
    is closest. On equal distances, a smaller distance in the x value is preferred.
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
    return [*left_initials, *right_initials]
