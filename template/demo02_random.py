# This bot takes random moves, chosen among the legal ones for its current
# position

TEAM_NAME = 'RandomBots'

def move(bot, state):
    # note our use of the internal random number generator
    # do *not* use a different one, or your games can not be replicated
    next_pos = bot.random.choice(bot.legal_positions)
    return next_pos, state
