""" collecting the game state filter functions """
from .base_utils import default_rng


def noiser(walls, shape, bot_position, enemy_positions, noise_radius=5, sight_distance=5, rng=None):
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
    rng : Random, optional
        the game’s random number generator (or None for an independent one)

    Returns
    -------
    dict { "enemy_positions": noised list of enemies, "is_noisy": list of bool }

    """

    # set the random state
    rng = default_rng(rng)

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
            new_pos, noisy_flag = alter_pos(b, noise_radius, rng, walls, shape)
            noised_positions[count] = new_pos
            is_noisy[count] = noisy_flag
        else:
            noised_positions[count] = b
            is_noisy[count] = False

    return { "enemy_positions": noised_positions, "is_noisy": is_noisy }


def alter_pos(bot_pos, noise_radius, rng, walls, shape):
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
        final_pos = rng.choice(possible_positions)
        noisy = True

    # return the final_pos and a flag if it is noisy or not
    return (final_pos, noisy)

def in_homezone(position, team_id, shape):
    boundary = shape[0] / 2
    if team_id == 0:
        return position[0] < boundary
    elif team_id == 1:
        return position[0] >= boundary


def update_food_age(game_state, team, radius):
    # Only ghosts can cast a shadow
    ghosts = [
        bot for bot in game_state['bots'][team::2]
        if in_homezone(bot, team, game_state['shape'])
    ]
    food = game_state['food'][team]
    food_age = [dict(team_food_age) for team_food_age in game_state['food_age']]

    for pellet in food:
        if any(manhattan_dist(ghost, pellet) <= radius for ghost in ghosts):
            if pellet in food_age[team]:
                food_age[team][pellet] += 1
            else:
                food_age[team][pellet] = 1
        else:
            if pellet in food_age[team]:
                del food_age[team][pellet]

    return {'food_age': food_age}


def relocate_expired_food(game_state, team, radius, max_food_age=None):
    bots = game_state['bots'][team::2]
    enemy_bots = game_state['bots'][1-team::2]
    food = [set(team_food) for team_food in game_state['food']]
    food_age = [dict(team_food_age) for team_food_age in game_state['food_age']]
    width, height = game_state['shape']
    walls = game_state['walls']
    rng = game_state['rng']
    if max_food_age is None:
        max_food_age = game_state['max_food_age']

    # generate a set of possible positions to relocate food:
    #  - in the bot's homezone
    #  - not a wall
    #  - not on a already present food pellet
    #  - not on a bot
    #  - not on the border
    #  - not within the shadow of a bot
    home_width = width // 2
    left_most_x = home_width * team
    targets = { (x, y) for x in range(left_most_x, left_most_x+home_width) # this line and the next define the homezone
                       for y in range(height)
                       if (x not in (home_width, home_width - 1) # this excludes the border
                           and manhattan_dist(bots[0], (x, y)) > radius # this line and the next excludes the team's bots and their shadows
                           and manhattan_dist(bots[1], (x, y)) > radius )
              }
    targets = targets.difference(walls) # remove the walls
    targets = targets.difference(food[team]) # remove the team's food
    targets = targets.difference(enemy_bots) # remove the enemy bots
    # now convert to a list and sort, so that we have reproducibility (sets are unordered)
    targets = sorted(list(targets))
    for pellet in sorted(list(food[team])):
        # We move the pellet if it is in the food_age dict and exceeds the max_food_age
        if food_age[team].get(pellet, 0) > max_food_age:
            if not targets:
                # we have no free positions anymore, just let the food stay where it is
                # we do not update the age, so this pellet will get a chance to be
                # relocated at the next round
                continue
            # choose a new position at random
            new_pos = rng.choice(targets)

            # remove the new pellet position from the list of possible targets for new pellets
            targets.remove(new_pos)

            # get rid of the old pellet
            food[team].remove(pellet)
            del food_age[team][pellet]

            # add the new pellet to food again
            # (starts with 0 food age, so we do not need to add it to the food_age dict)
            food[team].add(new_pos)

    return {'food' : food, 'food_age' : food_age}


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
