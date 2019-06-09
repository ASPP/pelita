from pelita.graph import Graph, NoPathException


def smart_eating_player(bot, state):
    if state is None:
        # first turn, first round
        state = {
            'graph': Graph(bot.position, bot.walls)
        }

    if not bot.turn in state:
        state[bot.turn] = {
            'next_food': None
        }

    # check, if food is still present
    if (state[bot.turn]['next_food'] is None
            or state[bot.turn]['next_food'] not in bot.enemy[0].food):
        if not bot.enemy[0].food:
            # all food has been eaten? ok. i’ll stop
            return bot.position, state
        state[bot.turn]['next_food'] = bot.random.choice(bot.enemy[0].food)

    try:
        dangerous_enemy_pos = [enemy.position for enemy in bot.enemy if enemy.position in enemy.homezone]

        next_pos = state['graph'].a_star(bot.position, state[bot.turn]['next_food'])[-1]
        # check, if the next_pos has an enemy on it
        if next_pos in dangerous_enemy_pos:
            # whoops, better wait this round and take another food next time
            state[bot.turn]['next_food'] = None
            return bot.position, state

        return next_pos, state
    except NoPathException:
        return bot.position, state


TEAM_NAME = "Smart Eating Players"
move = smart_eating_player
