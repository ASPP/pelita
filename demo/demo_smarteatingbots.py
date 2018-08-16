TEAM_NAME = 'SmartEatingBots'

from pelita.graph import Graph

def next_step(bot_position, target_position, graph):
    # return next step in the path to target_pos
    # where the path is generated with the a-star algorithm
    return graph.a_star(bot_position, target_position)[-1]

def move(turn, game):
    bot = game.team[turn]

    # we need to create a dictionary to keep information
    # over turns for each individual bot
    # - we want to track previous positions, so that we can backtrack if needed
    # - we want to keep track of the food pellet we are aiming at the moment
    if turn not in game.state:
        # initialize the dictionary for this bot
        game.state[turn] = {}

    # check if we already initialized a graph representation of the maze
    # this is shared between both our bots!
    if 'graph' not in game.state:
        # ok, initialize the graph
        game.state['graph'] = Graph(bot.position, bot.walls)

    # if we don't have a target food pellet, choose one at random now
    if 'target' not in game.state[turn]:
        game.state[turn]['target'] = bot.random.choice(bot.enemies[0].food)

    # if we are doing the first move, let's initialize a empty list to keep
    # track of our moves
    if 'track' not in game.state[turn]:
        game.state[turn]['track'] = []

    # did we (or the other bot) eat our target already?
    if game.state[turn]['target'] not in bot.enemies[0].food:
        # let's choose one random food pellet as our new goal
        game.state[turn]['target'] = bot.random.choice(bot.enemies[0].food)

    # get the next step to be done to reach our target food pellet
    next_pos = next_step(bot.position,
                         game.state[turn]['target'],
                         game.state['graph'])

    # now, let's check if we are getting too near to our enemies
    # where are the enemy ghosts?
    for enemy_pos in (bot.enemies[0].position, bot.enemies[1].position):
        if (next_pos == enemy_pos) and (next_pos not in bot.homezone):
            # we are in the enemy zone: they can eat us!
            # let us just step back
            next_pos = game.state[turn]['track'][-2]
            # let's forget about this food pellet and wait for next move to
            # choose another one
            game.state[turn].pop('target')

    # let's track our position
    game.state[turn]['track'].append(next_pos)

    return bot.get_direction(next_pos)

