# This bots moves randomly and if it gets eaten on the way, it cries out loud
TEAM_NAME = "Death Detectors Bots"

MESSAGE = 'I am a zombie now!'
EATEN_INERTIA = 10

def move(bot, state):

    if state is None:
        # initialize a state dictionary for both bots
        state = {0:0, 1:0}

    # check if we have been eaten in the previous round
    if bot.eaten:
        # set the speak inertia
        state[bot.turn] = EATEN_INERTIA

    if state[bot.turn]:
        # speak for as many rounds as EATEN_INTERTIA
        bot.say(MESSAGE)
        state[bot.turn] -= 1

    # copy the available positions, so that we can use random.shuffle,
    # which unfortunately shuffles lists in-place.
    legal_positions = bot.legal_positions[:]
    bot.random.shuffle(legal_positions)
    for new_pos in legal_positions:
        if new_pos not in bot.track:
           break

    return new_pos, state
