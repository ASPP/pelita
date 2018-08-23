# This bot moves randomly, but if there is a legal move that would allow it to
# eat food or eat an enemy, then this move is executed. Also, does not step
# on a ghost (no kamikaze).

TEAM_NAME = 'SmartRandomBots'

def move(turn, game):
    bot = game.team[turn]

    # go through all legal moves and check if there is one where we either:
    # - eat an enemy, or
    # - eat food
    # remove from the list of moves the ones where we would land on an enemy
    # on its homezone (kamikaze move)

    # get a tuple with our enemy positions
    enemy_pos = (bot.enemy[0].position, bot.enemy[1].position)

    # create a copy of the legal moves for our bot
    # important because we later need to modify this list in the loop
    # sensible_moves will be the list of moves among which we select the one
    # to make
    sensible_moves = bot.legal_moves[:]
    # loop through all legal moves
    for next_move in bot.legal_moves:
        # get the position we would be in if we would execute this move
        new_pos = bot.get_position(next_move)
        if (new_pos in enemy_pos) and (new_pos not in bot.homezone):
            # if we would step on a ghost we discard this move
            sensible_moves.remove(next_move)

    if len(sensible_moves) == 0:
        # we can't go anywhere safe
        # so just stop
        next_move = (0,0)
    else:
        # reshuffle the list of sensible moves
        bot.random.shuffle(sensible_moves)
        for next_move in sensible_moves:
            new_pos = bot.get_position(next_move)
            # if we are in our homezone, check if we can eat an enemy
            if new_pos in bot.homezone:
                # we are in our homezone
                if new_pos in enemy_pos:
                    # we can eat the enemy, accept the move
                    break
            else:
                # we are in the enemy zone
                if new_pos in bot.enemy[0].food:
                    # we can eat the food, accept the move
                    break

    # if we don't break out of the loop, we will do the last of the legal_moves
    return next_move
