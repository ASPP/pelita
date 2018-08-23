# This bot tries to catch an enemy bot. It will stop at the border of its
# homezone if the enemy is still in its own.

TEAM_NAME = 'Basic Defender Bots'

from pelita.graph import Graph

from utils import next_step

def move(turn, game):
    bot = game.team[turn]

    # we need to create a dictionary to keep information
    # over turns for each individual bot
    # - we want to keep track of the enemy we are aiming at the moment
    if turn not in game.state:
        # initialize the dictionary for this bot
        game.state[turn] = {}

    # check if we already initialized a graph representation of the maze
    # this is shared between both our bots!
    if 'graph' not in game.state:
        # ok, initialize the graph
        game.state['graph'] = Graph(bot.position, bot.walls)

    target = bot.enemy[turn].position

    # get the next step to be done to reach our target enemy bot
    next_pos = next_step(bot.position, target, game.state['graph'])

    # let's check that we don't go into the enemy homezone
    if next_pos in bot.enemy[turn].homezone:
        next_move = (0, 0)
    else:
        next_move = bot.get_move(next_pos)

    return next_move

