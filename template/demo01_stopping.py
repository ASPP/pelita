# This bot does not ever move (useful for testing)

TEAM_NAME = 'StoppingBots'

def move(bot, state):
    # do not move at all
    next_pos = bot.position
    return next_pos, state
