
from pelita.game import apply_move, next_round_turn
from pelita.player import food_eating_player
from pelita.team import Bot, _ensure_list_tuples, make_bots

def simulate_move(bot: Bot, next_pos):
    game_state = bot._game_state
    game_state['bots'] = _ensure_list_tuples(game_state['bots'])
    game_state['error_limit'] = 0
    game_state['gameover'] = False
    game_state['walls'] = bot.walls
    game_state['shape'] = bot.shape
    game_state['fatal_errors'] = [[], []]
    game_state['errors'] = [[], []]
    game_state['game_phase'] = 'RUNNING'

    game_state = apply_move(game_state, next_pos)
    game_state.update(next_round_turn(game_state))


    for tidx in range(2):
        game_state['food'][tidx] = _ensure_list_tuples(game_state['food'][tidx])
        game_state['shaded_food'][tidx] = _ensure_list_tuples(game_state['shaded_food'][tidx])

    next_bot = make_bots(bot_positions=game_state['bots'],
                        is_noisy=game_state['is_noisy'],
                        walls=bot.walls,
                        shape=bot.shape,
                        food=game_state['food'],
                        shaded_food=game_state['shaded_food'],
                        round=game_state['round'],
                        turn=game_state['turn'],
                        score=game_state['score'],
                        deaths=game_state['deaths'],
                        kills=game_state['kills'],
                        bot_was_killed=game_state['bot_was_killed'],
                        error_count=game_state['error_count'],
                        initial_positions=[bot._initial_position, bot.other._initial_position, bot._initial_position, bot.other._initial_position],
                        homezone=[bot.other.homezone, bot.homezone],
                        team_names=game_state['team_names'],
                        team_time=game_state['team_time'],
                        rng="bot._rng",
                        graph=bot.graph)

    return next_bot



def smart_eating_player(bot, state):

    print(simulate_move(bot, next_pos=bot.position))

    # food eating player but won’t do kamikaze (although a sufficiently smart
    # enemy will be able to kill the bot in its next turn as it doesn’t flee)
    next_pos = food_eating_player(bot, state)

    dangerous_enemy_pos = [enemy.position for enemy in bot.enemy if enemy.position in enemy.homezone]

    # check, if the next_pos has an enemy on it
    if next_pos in dangerous_enemy_pos:
        # whoops, better wait this round and take another food next time
        state[bot.turn]['next_food'] = None
        return bot.position

    return next_pos


TEAM_NAME = "Smart Eating Players"
move = smart_eating_player
