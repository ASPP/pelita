TEAM_NAME = 'SmartRandomBots'

def position_after_move(current_position, move):
    pos_x = current_position[0]+move[0]
    pos_y = current_position[1]+move[1]
    return (pos_x, pos_y)

def move(turn, game):
    bot = game.team[turn]

    # go through all legal moves and check if there is one where we either:
    # - eat an enemy, or
    # - eat food
    # remove from the list of moves the ones where we would land on an enemy
    # on its homezone
    sensible_moves = bot.legal_moves[:]
    enemy_pos = (bot.enemies[0].position, bot.enemies[1].position)

    for next_move in bot.legal_moves:
        new_pos = position_after_move(bot.position, next_move)
        if (new_pos in enemy_pos) and (new_pos not in bot.homezone):
            sensible_moves.pop(next_move)

    if len(sensible_moves) == 0:
        # we can't go anywhere safe
        next_move = (0,0)
    else:
        # reshuffle the list of sensible moves
        bot.random.shuffle(sensible_moves)
        for next_move in sensible_moves:
            new_pos = position_after_move(bot.position, next_move)
            # if we are in our homezone, check if we can eat an enemy
            if new_pos in bot.homezone:
                # we are in our homezone
                if new_pos in enemy_pos:
                    # we can eat the enemy, accept the move
                    break
            else:
                # we are in the enemy zone
                if new_pos in bot.enemies[0].food:
                    # we can eat the food, accept the move
                    break

    # if we don't break out of the loop, we will do the last of the legal_moves
    return next_move
