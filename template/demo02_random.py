# This bot takes random moves, chosen among the legal ones for its current
# position

TEAM_NAME = 'RandomBots'

def move(turn, game):
    # make a reference to our bot with a shorter name
    # mostly useful for longer code, of course
    bot = game.team[turn]
    return bot.random.choice(bot.legal_moves)
