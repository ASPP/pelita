# This bots goes for food and if it gets eaten on the way, it cries out loud
TEAM_NAME = "Death Detectors Bots"

MESSAGE = 'I am a zombie now!'
EATEN_INERTIA = 10

def move(turn, game):
    bot = game.team[turn]

    if game.state is None:
        # initialize a state dictionary for both bots
        game.state = { 0:0, 1:0}

    # check if we have benn eaten in the previous round
    if bot.eaten:
        # set the speak inertia
        game.state[turn] = EATEN_INERTIA
    if game.state[turn]:
        # speak for as many rounds as EATEN_INTERTIA
        bot.say(MESSAGE)
        game.state[turn] -= 1

    # copy the available moves, so that we can use random.shuffle,
    # which unfortunately shuffles lists in-place.
    legal_moves = bot.legal_moves[:]
    bot.random.shuffle(legal_moves)
    for next_move in legal_moves:
        new_pos = bot.get_position(next_move)
        if new_pos not in bot.track:
           break

    return next_move
