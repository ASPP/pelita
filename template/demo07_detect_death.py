# This bots moves randomly and if it gets killed on the way, it cries out loud
TEAM_NAME = "Death Detectors Bots"

MESSAGE = 'I am a zombie now!'
SPEAK_INERTIA = 10

from talk_util import say_underlined

def move(bot, state):
    if state == {}:
        # initialize a state dictionary for both bots
        state[0] = 0
        state[1] = 1

    # check if we have been killed in the previous round
    if bot.was_killed:
        # set the speak inertia
        state[bot.turn] = SPEAK_INERTIA

    if state[bot.turn]:
        # speak for as many rounds as SPEAK_INERTIA
        say_underlined(bot, MESSAGE)
        state[bot.turn] -= 1

    # copy the available positions, so that we can use random.shuffle,
    # which unfortunately shuffles lists in-place.
    legal_positions = bot.legal_positions[:]
    bot.random.shuffle(legal_positions)
    for new_pos in legal_positions:
        if new_pos not in bot.track:
           break

    return new_pos
