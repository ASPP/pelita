""" collecting the game state filter functions """
import random


def noiser(walls, shape, bot_position, enemy_positions, noise_radius=5, sight_distance=5, rnd=None):
    """Function to make bot positions noisy in a game state.

    Applies uniform noise in maze space. Noise will only be applied if the
    enemy bot is farther away than a certain threshold (`sight_distance`),
    which is Manhattan distance disregarding walls. A bot with distance of 1 in
    Manhattan space could still be much further away in maze distance.

    Distance to enemies measured in Manhattan space, disregarding walls. So, a
    bot distance of 1 in Manhattan space could still be much further away in
    maze distance.

    Given a `bot_position` and a list of `enemy_positions`, this function adds
    uniform noise in maze space to the enemy positions, but only if bot is
    farther away than sight_distance.

    The function returns a dictionary with entries `"enemy_positions"` (which
    holds the list of new enemy positions) and `"is_noisy"` (which is a list of
    bool, saying which enemy index is noisy).

    Functions needed
    ----------------

    altered_pos(bot_pos):
        return the noised new position of an enemy bot.

    manhattan_dist(a,b):
        returns a scalar

    Parameters
    ----------
    walls : set of (int, int)
    noise_radius : int, optional, default: 5
        the radius for the uniform noise
    sight_distance : int, optional, default: 5
        the distance at which noise is no longer applied.
    rnd : Random, optional
        the game’s random number generator (or None for an independent one)

    Returns
    -------
    dict { "enemy_positions": noised list of enemies, "is_noisy": list of bool }

    """

    # set the random state
    if rnd is None:
        rnd = random.Random()

    # store the noised positions
    noised_positions = [None] * len(enemy_positions)

    # store, if an enemy is noisy
    is_noisy = [None] * len(enemy_positions)

    for count, b in enumerate(enemy_positions):
        # Check that the distance between this bot and the enemy is larger
        # than `sight_distance`.
        cur_distance = manhattan_dist(bot_position, b)

        if cur_distance is None or cur_distance > sight_distance:
            # If so then alter the position of the enemy
            new_pos, noisy_flag = alter_pos(b, noise_radius, rnd, walls, shape)
            noised_positions[count] = new_pos
            is_noisy[count] = noisy_flag
        else:
            noised_positions[count] = b
            is_noisy[count] = False

    return { "enemy_positions": noised_positions, "is_noisy": is_noisy }


def alter_pos(bot_pos, noise_radius, rnd, walls, shape):
    """ alter the position """

    # get a list of possible positions
    x_min, x_max = bot_pos[0] - noise_radius, bot_pos[0] + noise_radius
    y_min, y_max = bot_pos[1] - noise_radius, bot_pos[1] + noise_radius

    # filter them so that we return no positions outside the maze
    if x_min < 0:
        x_min = 1
    if x_max >= shape[0]:
        x_max = shape[0] - 1
    if y_min < 0:
        y_min = 1
    if y_max >= shape[1]:
        y_max = shape[1] - 1

    possible_positions = [
        (i, j)
        for i in range(x_min, x_max + 1) # max + 1 since range is not inclusive at upper end
        for j in range(y_min, y_max + 1) # max + 1 since range is not inclusive at upper end
        if manhattan_dist((i, j), bot_pos) <= noise_radius
        and not (i, j) in walls # check that the bot won't returned as positioned on a wall square
    ]

    if len(possible_positions) < 1:
        # this should not happen
        # anyway. return the bot’s current position
        # TODO: Should probably raise?
        final_pos = bot_pos
        noisy = False
    elif len(possible_positions) == 1:
        final_pos = possible_positions[0]
        noisy = False
    else:
        # select a random position
        final_pos = rnd.choice(possible_positions)
        noisy = True

    # return the final_pos and a flag if it is noisy or not
    return (final_pos, noisy)

def in_homezone(position, team_id, shape):
    boundary = shape[0] / 2
    if team_id == 0:
        return position[0] < boundary
    elif team_id == 1:
        return position[0] >= boundary


def update_food_lifetimes(game_state, radius):
    shape = game_state['shape']
    bots = game_state['bots']
    team_food = game_state['food']
    food_lifetime = dict(game_state['food_lifetime'])

    for team_idx in [0, 1]:
        team_bot_pos = bots[team_idx::2]
        for food_pos in team_food[team_idx]:
            if any(manhattan_dist(food_pos, bot_pos) < radius and in_homezone(bot_pos, team_idx, shape)
                    for bot_pos in team_bot_pos):
                food_lifetime[food_pos] -= 1
            else:
                food_lifetime[food_pos] = 60

    return {'food_lifetime': food_lifetime}

def find_free_pos(shape, walls, food_to_keep, team_id):
    # Finds a position in the homezone on team_id that has no walls and no food
    if team_id == 0:
        range_x = [0, shape[0] // 2]
    else:
        range_x = [shape[0] // 2, shape[0]]
    range_y = [0, shape[1]]
    while True:
        x = random.randrange(*range_x)
        y = random.randrange(*range_y)
        pos = (x, y)
        if pos not in walls and pos not in food_to_keep:
            return pos


def relocate_expired_food(game_state):
    team_food = game_state['food']
    food_lifetime = dict(game_state['food_lifetime'])
    shape = game_state['shape']
    walls = game_state['walls']

    res_food = []

    for team_idx in [0, 1]:
        food_to_relocate = set()
        food_to_keep = set()
        for food_pos in team_food[team_idx]:
            if food_lifetime[food_pos] == 0:
                food_to_relocate.add(food_pos)
                del food_lifetime[food_pos]
            else:
                food_to_keep.add(food_pos)

        for relocate in food_to_relocate:
            new_pos = find_free_pos(shape, walls, food_to_keep, team_idx)
            food_to_keep.add(new_pos)
            food_lifetime[new_pos] = 60

        res_food.append(food_to_keep)

    res = {
        "food": res_food,
        "food_lifetime": food_lifetime
    }

    return res

def manhattan_dist(pos1, pos2):
    """ Manhattan distance between two points.

    Parameters
    ----------
    pos1 : tuple of (int, int)
        the first position
    pos2 : tuple of (int, int)
        the second position

    Returns
    -------
    manhattan_dist : int
        Manhattan distance between two points
    """
    return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])
