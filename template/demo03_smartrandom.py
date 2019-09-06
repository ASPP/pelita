# This bot moves randomly, with some improvements:
# - it kills enemies in the vicinity
# - it eats food in the vicinity
# - does not do kamikaze
# - avoids going back to positions it has seen already
TEAM_NAME = 'SmartRandomBots'

def move(bot, state):
    enemy = bot.enemy
    # get a tuple with our enemy positions
    enemy_pos = (enemy[0].position, enemy[1].position)

    # sensible positions are all legal positions that do not cause death
    sensible_positions = bot.legal_positions[:]
    # if we would step on a ghost outside our homezone we discard this move
    for next_pos in bot.legal_positions:
        if (next_pos in enemy_pos) and (next_pos not in bot.homezone):
            sensible_positions.remove(next_pos)

    if len(sensible_positions) == 0:
        # we can't go anywhere safe
        # so just stop here and hope for the best
        next_pos = bot.position
    else:
        # we can do something without risk

        # collect positions that have something interesting in it (food can be
        # eaten or enemy can be killed)
        interesting_positions = []
        for new_pos in sensible_positions:
            # the new position is interesting if
            # 1. we are in our homezone and we can kill an enemy
            cond1 = (new_pos in bot.homezone) and (new_pos in enemy_pos)
            # or, if 2. we are in enemy's homezone and we can eat food
            cond2 = (new_pos in enemy[0].homezone) and (new_pos in enemy[0].food)
            if cond1 or cond2:
                    # if either one condition is met, this position is interesting
                    interesting_positions.append(new_pos)
        # now we have scanned all sensible positions
        # do we have any interesting left?
        if len(interesting_positions) > 0:
            # yes, so choose one at random
            next_pos = bot.random.choice(interesting_positions)
        else:
            # all sensible positions are equally (un)interesting, so pick
            # one that we haven't seen already
            for next_pos in sensible_positions:
                if next_pos not in bot.track:
                    break
            # if we don't break out of the loop early it means that all new
            # positions have been visited already, so we just pick the
            # last one in the list

    return next_pos
