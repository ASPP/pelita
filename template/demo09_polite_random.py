# This bot takes random moves, chosen among the legal ones for its current
# position, but will not step on its teammate's toes.

TEAM_NAME = 'PoliteRandomBots'

def move(bot, state):

    possible_moves = []
    for pos in bot.legal_positions:
        if pos == bot.other.position:
            bot.say('Excuse me. Sorry. Excuse me.')
        else:
            possible_moves.append(pos)
    # possible_moves is never empty, because we can either:
    # - move away from our team mate if we already are in the same position, or
    # - we can stop if our only other legal move would put us in the same
    #   position as our team mate
    next_move = bot.random.choice(possible_moves)
    return next_move, state
