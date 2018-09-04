import time
# This bot takes random moves, chosen among the legal ones for its current
# position, but will not step on its teammate's toes.

TEAM_NAME = 'PoliteRandomBots'

def move(turn, game):
    bot = game.team[turn]
    teammate = game.team[1 - turn]
    x0, y0 = bot.position
    x1, y1 = teammate.position
    move_to_teammate = (x0 - x1, y0 - y1)
    possible_moves = bot.legal_moves[:]
    if move_to_teammate in possible_moves:
        bot.say('Oh. You go first.')
        teammate.say('No, you.')
        time.sleep(0.5)
        bot.say('Please.')
        teammate.say('I insist.')
        possible_moves.remove(move_to_teammate)
    return bot.random.choice(bot.possible_moves)
