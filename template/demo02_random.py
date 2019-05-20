# This bot takes random moves, chosen among the legal ones for its current
# position

TEAM_NAME = 'RandomBots'

def move(bot, state):
    # make a reference to our bot with a shorter name
    # mostly useful for longer code, of course
    next_move = bot.random.choice(bot.legal_positions)
    return next_move, state
