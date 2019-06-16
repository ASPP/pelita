# This bot takes random moves, chosen among the legal ones for its current
# position, but will not step on its teammate's toes.

TEAM_NAME = 'PoliteRandomBots'

def move(bot, state):

    possible_positions = []
    for pos in bot.legal_positions:
        if pos == bot.other.position:
            bot.say('Excuse me. Sorry. Excuse me.')
        else:
            possible_positions.append(pos)
    # possible_positions is never empty, because we can either:
    # - move away from our team mate if we already are in the same position, or
    # - we can stop if our only other legal position would put us in the same
    #   position as our team mate
    next_pos = bot.random.choice(possible_positions)
    return next_pos, state
