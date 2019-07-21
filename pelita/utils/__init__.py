import random

from ..player.team import create_layout, make_bots
from ..graph import Graph

def split_food(layout):
    width = max(layout.walls)[0] + 1

    team_food = [set(), set()]
    for pos in layout.food:
        idx = pos[0] // (width // 2)
        team_food[idx].add(pos)
    return team_food


def setup_test_game(*, layout, game=None, is_blue=True, round=None, score=None, seed=None,
                    food=None, bots=None, enemy=None):
    """Returns the first bot object given a layout.

    The returned Bot instance can be passed to a move function to test its return value.
    The layout is a string that can be passed to create_layout."""
    if game is not None:
        raise RuntimeError("Re-using an old game is not implemented yet.")

    if score is None:
        score = [0, 0]

    layout = create_layout(layout, food=food, bots=bots, enemy=enemy)
    food = split_food(layout)

    if is_blue:
        team_index = 0
        enemy_index = 1
    else:
        team_index = 1
        enemy_index = 0

    rng = random.Random(seed)

    team = {
        'bot_positions': layout.bots[:],
        'team_index': team_index,
        'score': score[team_index],
        'kills': [0]*2,
        'deaths': [0]*2,
        'bot_eaten' : [False]*2,
        'timeout_count': 0,
        'food': food[team_index],
        'name': "blue" if is_blue else "red"
    }
    enemy = {
        'bot_positions': layout.enemy[:],
        'team_index': enemy_index,
        'score': score[enemy_index],
        'kills': [0]*2,
        'deaths': [0]*2,
        'bot_eaten': [False]*2,
        'timeout_count': 0,
        'food': food[enemy_index],
        'is_noisy': [False] * len(layout.enemy),
        'name': "red" if is_blue else "blue"
    }

    bot = make_bots(walls=layout.walls[:],
                    team=team,
                    enemy=enemy,
                    round=round,
                    bot_turn=0,
                    rng=rng)
    return bot

