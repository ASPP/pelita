# This bot takes random moves, chosen among the legal ones for its current
# position, but will not step on its teammate's toes.

TEAM_NAME = 'PoliteRandomBots'

def move(turn, game):
    bot = game.team[turn]
    teammate = game.team[1 - turn]

    possible_moves = []
    for m in bot.legal_moves:
        if bot.get_position(m) == teammate.position:
            bot.say('Excuse me. Sorry. Excuse me.')
        else:
            possible_moves.append(m)
    # bot.legal_moves should always contain at least two moves
    # so possible_moves will contain at least one move
    # (therefore random.choice will not break)
    return bot.random.choice(possible_moves)
