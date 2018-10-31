# This bot selects a food pellet at random, then goes and tries to get it by
# following the shortest path to it.
# It tries on the way to avoid being eaten by the enemy: if the next move
# to get to the food would put it on a ghost, then it steps back to its
# previous position
TEAM_NAME = 'Basic Attacker Bots'

from pelita.utils import Graph

from utils import next_step

def move(bot, state):
    # we need to create a dictionary to keep information (state) along rounds
    # the state object will be passed untouched at every new round
    if state is None:
        # initialize the state dictionary
        state = {}
        # each bot needs its own state dictionary to keep track of the
        # food targets
        state[0] = None
        state[1] = None
        # initialize a graph representation of the maze
        # this can be shared among our bots
        state['graph'] = Graph(bot.position, bot.walls)

    target = state[bot.turn]

    # choose a target food pellet if we still don't have one or
    # if the old target has been already eaten
    if (target is None) or (target not in bot.enemy[0].food):
        target = state[bot.turn] = bot.random.choice(bot.enemy[0].food)

    # get the next position along the shortest path to reach our target
    next_pos = next_step(bot.position, target, state['graph'])

    # now, let's check if we are getting too near to our enemy
    # where are the enemy ghosts?
    for enemy_pos in (bot.enemy[0].position, bot.enemy[1].position):
        if (next_pos == enemy_pos) and (next_pos not in bot.homezone):
            # we are in the enemy zone: they can eat us!
            # 1. let's forget about this target (the enemy is sitting on it for
            #    now). We will choose a new target in the next round
            state[bot.turn] = None
            # 2. let us step back
            # bot.track[-1] is always the current position, so to backtrack
            # we select bot.track[-2]
            next_pos = bot.track[-2]
            if next_pos == enemy_pos:
                # we would step back on a ghost who is chasing us, let us just
                # take a random move
                next_pos = bot.get_position(bot.random.choice(bot.legal_moves))

    # return the move needed to get from our position to the next position
    next_move = bot.get_move(next_pos)
    return next_move, state

