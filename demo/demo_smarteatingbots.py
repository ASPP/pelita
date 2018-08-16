TEAM_NAME = 'SmartEatingBots'

from pelita.graph import Graph

def next_step(bot_position, target_position, graph):
    # return next step in the path to target_pos
    # where the path is generated with the a-star algorithm
    return graph.a_star(bot_position, target_position)[-1]

def move(turn, game):
    bot = game.team[turn]

    # check if we have eaten all the food?
    if len(bot.enemies[0].food) == 0:
        return (0, 0)

    if turn not in game.state:
        # let’s track the goal for _this_ bot in our game.state
        game.state[turn] = bot.random.choice(bot.enemies[0].food)

    # check if we already initialized a graph representation of the maze
    # we put this in the team_state dictionary because it is the same
    # for both bots
    if 'graph' not in game.state:
        # ok, initialize the graph
        game.state['graph'] = Graph(bot.position, bot.walls)

    # did we (or the other bot) eat it already?
    if game.state[turn] not in bot.enemies[0].food:
        # let's choose one random food pellet as our new goal
        game.state[turn] = bot.random.choice(bot.enemies[0].food)

    # get the next step to be done to reach our goal food pellet
    next_pos = next_step(bot.position, game.state[turn], game.state['graph'])
    # now, let's check if we are getting too near to our enemies
    # where are the enemy destroyers?

    for enemy_pos in (bot.enemies[0].position, bot.enemies[1].position):
        if (next_pos == enemy_pos) and (next_pos not in bot.homezone):
            # we are in the enemy zone: they can eat us!
            # let us just step back
            # note that this only works if the maze is big enough to have
            # a home zone bigger than two squares
            next_pos = bot.track[-2]
            # let's forget about this food pellet and wait for next move to
            # choose another one
            game.state.pop(turn)

    return bot.get_direction(next_pos)

