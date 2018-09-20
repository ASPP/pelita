# This bot moves randomly, with some improvements:
# - it eats enemies in the vicinity
# - it eats food in the vicinity
# - does not do kamikaze
# - avoids going back to positions it has seen already
TEAM_NAME = 'SmartRandomBots'

def move(bot, state):
    # get a tuple with our enemy positions
    enemy_pos = (bot.enemy[0].position, bot.enemy[1].position)

    # sensible moves are all legal moves that do not cause death
    sensible_moves = bot.legal_moves[:]
    # loop through all legal moves
    for next_move in bot.legal_moves:
        # get the position we would be in if we would execute this move
        new_pos = bot.get_position(next_move)
        if (new_pos in enemy_pos) and (new_pos not in bot.homezone):
            # if we would step on a ghost we discard this move
            sensible_moves.remove(next_move)


    if len(sensible_moves) != 0:
        # we can do something without risk

        # collect positions that have something interesting in it (food or enemy to
        # be eaten
        interesting_positions = []
        # reshuffle the list of sensible moves
        bot.random.shuffle(sensible_moves)
        for next_move in sensible_moves:
            new_pos = bot.get_position(next_move)
            # the new position is interesting if
            # 1. we are in our homezone and we can eat an enemy
            cond1 = (new_pos in bot.homezone) and (new_pos in enemy_pos)
            # 2. we are in enemy's homezone and we can eat food
            enemy_home = bot.enemy[0].homezone
            food = bot.enemy[0].food
            cond2 = (new_pos in enemy_home) and (new_pos in food)
            if cond1 or cond2:
                    # either one condition is met, this position is interesting
                    interesting_positions.append(new_pos)
        # now we have scanned all sensible moves.
        # do we have any interesting moves to do?
        if len(interesting_positions) > 0:
            # yes, so choose one at random
            next_move = bot.get_move(bot.random.choice(interesting_positions))
        else:
            # all sensible moves are equally interesting, so pick
            # one that we haven't seen already
            for next_move in sensible_moves:
                new_pos = bot.get_position(next_move)
                if new_pos not in bot.track:
                    break
            # if we don't break out of the loop early it means that all new
            # positions have been visited already, so we just pick the
            # last one in the list
    else:
        # we can't go anywhere safe
        # so just stop here and hope for the best
        next_move = (0,0)

    return next_move, state
