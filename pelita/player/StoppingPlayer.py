def stopping_player(bot, state):
    """ A Player that just stands still. """
    return bot.position, state

TEAM_NAME = "Stopping Players"
move = stopping_player
