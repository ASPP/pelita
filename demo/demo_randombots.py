TEAM_NAME = 'RandomBots'

def move(turn, game):
    bot = game.team[turn]
    return bot.random.choice(bot.legal_moves)
