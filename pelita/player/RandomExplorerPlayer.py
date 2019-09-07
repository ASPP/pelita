
def random_explorer_player(bot, state):
    """ Least visited random player. Will prefer moving to a position it’s never seen before. """

    if not bot.turn in state:
        # initialize bot
        state[bot.turn] = { 'visited': [] }

    if bot.position in state[bot.turn]['visited']:
        state[bot.turn]['visited'].remove(bot.position)
    state[bot.turn]['visited'].insert(0, bot.position)

    # possible candidates
    positions = bot.legal_positions[:]
    # go through all visited positions and remove them
    # from our candidate list
    for pos in state[bot.turn]['visited']:
        if len(positions) == 1:
            # only one position left, we’ll take it
            return positions[0]
        if len(positions) == 0:
            return bot.position
        if pos in positions:
            positions.remove(pos)

    # more than one move left
    return bot.random.choice(positions)


TEAM_NAME = "Random Explorer Players"
move = random_explorer_player
