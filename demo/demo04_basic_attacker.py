# This bot selects a food pellet at random, then goes and tries to get it by
# following the shortest path to it.
# It tries on the way to avoid being eaten by the enemy: if the next move
# to get to the food would put it on a ghost, then it chooses a random safe
# position
TEAM_NAME = 'Basic Attacker Bots'

from pelita.utils import Graph

from utils import shortest_path


def move(bot, state):
    enemy = bot.enemy
    # we need to create a dictionary to keep information (state) along rounds
    # the state object will be passed untouched at every new round
    if state is None:
        # initialize the state dictionary
        state = {}
        # each bot needs its own state dictionary to keep track of the
        # food targets
        state[0] = (None, None)
        state[1] = (None, None)
        # initialize a graph representation of the maze
        # this can be shared among our bots
        state['graph'] = Graph(bot.position, bot.walls)

    target, path = state[bot.turn]

    # choose a target food pellet if we still don't have one or
    # if the old target has been already eaten
    if (target is None) or (target not in enemy[0].food):
        # position of the target food pellet
        target = bot.random.choice(enemy[0].food)
        # shortest path from here to the target
        path = shortest_path(bot.position, target, state['graph'])
        state[bot.turn] = (target, path)

    # get the next position along the shortest path to reach our target
    next_pos = path.pop()
    # get a list of safe positions
    safe_positions = []
    for pos in bot.legal_positions:
        # a position is safe if the enemy is not sitting on it *and*
        # the enemy does not sit in the neighborhood of that position
        safe = True
        for direction in ((0, 0), (0,1), (0,-1), (1,0), (-1,0)):
            neighbor = (pos[0]+direction[0], pos[1]+direction[1])
            if neighbor in (enemy[0].position, enemy[1].position):
                safe = False
                break
        if safe:
            safe_positions.append(pos)

    # we now may have duplicates in the list of safe positions -> get rid
    # of them not to bias the random choice
    safe_positions = list(set(safe_positions))

    # are we about to move to an unsafe position?
    if next_pos not in safe_positions:
        # 1. Let's forget about this target and this path
        #    We will choose a new target in the next round
        state[bot.turn] = (None, None)
        # Choose one safe position at random if we have any
        if safe_positions:
            next_pos = bot.random.choice(safe_positions)
        else:
            # we are doomed anyway
            next_pos = bot.position

    return next_pos, state

