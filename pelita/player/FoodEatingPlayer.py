from pelita.graph import Graph, NoPathException

def food_eating_player(bot, state):
    if state is None:
        # first turn, first round
        state = {
            'graph': Graph(bot.position, bot.walls)
        }

    if not bot.turn in state:
        state[bot.turn] = {
            'next_food': None
        }

    # check if food is still there for us to eat
    if (state[bot.turn]['next_food'] is None
        or state[bot.turn]['next_food'] not in bot.enemy[0].food):
        if not bot.enemy[0].food:
            # all food has been eaten? ok. I’ll stop
            next_pos = bot.position
            return next_pos, state

        state[bot.turn]['next_food'] = bot.random.choice(bot.enemy[0].food)

    try:
        next_pos = state['graph'].a_star(bot.position, state[bot.turn]['next_food'])[-1]
    except NoPathException:
        next_pos = bot.position

    return next_pos, state


TEAM_NAME = "The Smart Eating Players"
move = food_eating_player
