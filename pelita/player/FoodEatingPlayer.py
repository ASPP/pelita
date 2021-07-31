import networkx

from pelita.utils import walls_to_graph


def food_eating_player(bot, state):
    if 'graph' not in state:
        # first turn, first round
        state['graph'] = walls_to_graph(bot.walls)

    if bot.turn not in state:
        state[bot.turn] = { 'next_food': None }

    # check if food is still there for us to eat
    if (state[bot.turn]['next_food'] is None
        or state[bot.turn]['next_food'] not in bot.enemy[0].food):
        if not bot.enemy[0].food:
            # all food has been eaten? ok. I’ll stop
            # NB: We should never land here; the game will be over instead
            next_pos = bot.position
            return next_pos

        state[bot.turn]['next_food'] = bot.random.choice(bot.enemy[0].food)

    # the first position in the shortest path is always bot.position
    next_pos = networkx.shortest_path(state['graph'], bot.position, state[bot.turn]['next_food'])[1]

    return next_pos


TEAM_NAME = "Food Eating Players"
move = food_eating_player
