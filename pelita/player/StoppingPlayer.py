def stopping_player(bot, state):
    """ A Player that just stands still. """
    bot.say("Guarding")
    return bot.position

TEAM_NAME = "Guarding Players"
move = stopping_player
