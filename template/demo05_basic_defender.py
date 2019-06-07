# This bot tries to catch an enemy bot. It will stop at the border of its
# homezone if the enemy still did not cross the border.
# As long as the enemies are far away (their position is noisy), the bot
# tries to get near to the bot in the enemy team which has the same turn.
# As soon as an enemy bot is not noisy anymore, i.e. it has come near, the
# bot goes after it and leaves the other enemy alone

TEAM_NAME = 'Basic Defender Bots'

from pelita.utils import Graph

from utils import next_step


def move(bot, state):

    if state is None:
        # initialize the state object to be a graph representation of the maze
        state = Graph(bot.position, bot.walls)

    turn = bot.turn
    if bot.enemy[0].is_noisy and bot.enemy[1].is_noisy:
        # if both enemies are noisy, just aim for our turn companion
        target = bot.enemy[turn].position
    elif not bot.enemy[turn].is_noisy:
        # if our turn companion is not noisy, go for it
        target = bot.enemy[turn].position
    elif not bot.enemy[1-turn].is_noisy:
        # if the other enemy is not noisy, go for it
        target = bot.enemy[1-turn].position
    else:
        raise Exception('We should never be here!')

    # get the next step to be done to reach our target enemy bot
    next_pos = next_step(bot.position, target, state)

    # let's check that we don't go into the enemy homezone, i.e. stop at the
    # border
    if next_pos in bot.enemy[turn].homezone:
        next_pos = bot.position

    return next_pos, state

