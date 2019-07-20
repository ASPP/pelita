# This bots moves randomly and if it gets eaten on the way, it cries out loud
TEAM_NAME = "Death Detectors Bots"

MESSAGE = 'I was killed '

def move(bot, state):
    # update the death count for this bot
    ndeaths = sum(bot.deaths)

    if ndeaths > 0:
        bot.say(MESSAGE + f'{ndeaths} time(s)!')

    # copy the available positions, so that we can use random.shuffle,
    # which unfortunately shuffles lists in-place.
    legal_positions = bot.legal_positions[:]
    bot.random.shuffle(legal_positions)
    for new_pos in legal_positions:
        if new_pos not in bot.track:
           break

    return new_pos, state
