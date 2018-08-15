TEAM_NAME = 'SmartEatingBots'

from pelita.utils import Graph

def next_step(bot_position, target_position, graph):
    # return next step in the path to target_pos
    # where the path is generated with the a-star algorithm
    return graph.a_star(bot.position, target_position)[-1]

def move1(bot, bot_state, team_state):
    # check if we already initialized a graph representation of the maze
    # we put this in the team_state dictionary because it is the same
    # for both bots
    if 'graph' not in team_state:
        # ok, initialize the graph
        team_state['graph'] = Graph(bot.reachable_positions)

    # do I already have a goal?
    if 'goal' not in bot_state:
        # let's choose one random food pellet as our goal
        bot_state['goal'] = bot.random.choice(bot.enemy_food)

    # get the next step to be done to reach our goal food pellet
    next_pos = next_step(bot.position, bot_state['goal'], team_state['graph'])
    # now, let's check if we are getting too near to our enemies
    # where are the enemy destroyers?
    for enemy_pos in bot.enemy_positions:
        if (next_pos == enemy_pos) and (next_pos not in bot.homezone):
            # we are in the enemy zone: they can eat us!
            # let us just step back
            # note that this only works if the maze is big enough to have
            # a home zone bigger than two squares
            next_pos = bot.track[-2]
            # let's forget about this food pellet and wait for next move to
            # choose another one
            bot_state.pop('goal')

    return bot.get_direction(next_pos)

# both our bots use the same strategy, just different random goals
move2 = move1
