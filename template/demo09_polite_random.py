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
    # possible_moves is never empty, because we can either:
    # - move away from our team mate if we already are in the same position, or
    # - we can stop if our only other legal move would put us in the same
    #   position as our team mate
    return bot.random.choice(possible_moves)
