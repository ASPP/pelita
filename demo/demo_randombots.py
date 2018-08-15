TEAM_NAME = 'RandomBots'

def move1(bot, bot_state, team_state):
    return bot.random.choice(bot.legal_moves)

# both our bots use the same strategy
move2 = move1
