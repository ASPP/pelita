# This bot does not ever move (useful for testing)

TEAM_NAME = 'StoppingBots'

def move(bot, state):
    # do not move at all
    return bot.position
