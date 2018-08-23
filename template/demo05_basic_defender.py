# This bot tries to catch an enemy bot. It will stop at the border of its
# homezone if the enemy is still in its own.

TEAM_NAME = 'Basic Defender Bots'

from pelita.graph import Graph

from utils import next_step

def move(turn, game):
    bot = game.team[turn]

    if game.state is None:
        # initialize the state for the team to be a graph representation of the
        # maze
        game.state = Graph(bot.position, bot.walls)

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
    next_pos = next_step(bot.position, target, game.state)

    # let's check that we don't go into the enemy homezone
    if next_pos in bot.enemy[turn].homezone:
        next_move = (0, 0)
    else:
        next_move = bot.get_move(next_pos)

    return next_move

