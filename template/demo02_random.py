# This bot takes random moves, chosen among the legal ones for its current
# position

TEAM_NAME = 'RandomBots'

def move(turn, game):
    bot = game.team[turn]
    return bot.random.choice(bot.legal_moves)
