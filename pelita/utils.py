import logging
import random

from .player.team import create_layout, make_bots
from .graph import Graph


def start_logging(filename, module='pelita'):
    if not filename or filename == '-':
        hdlr = logging.StreamHandler()
    else:
        hdlr = logging.FileHandler(filename, mode='w')
    logger = logging.getLogger(module)
    FORMAT = '[%(relativeCreated)06d %(name)s:%(levelname).1s][%(funcName)s] %(message)s'
    formatter = logging.Formatter(FORMAT)
    hdlr.setFormatter(formatter)
    logger.addHandler(hdlr)
    logger.setLevel(logging.DEBUG)


def split_food(width, food):
    team_food = [set(), set()]
    for pos in food:
        idx = pos[0] // (width // 2)
        team_food[idx].add(pos)
    return team_food


def bot_to_gamestate(bot):
    if bot.is_blue:
        turn = bot.turn * 2
        teams = [bot, bot.enemy[0]]
        bots = [bot._bots['team'][0], bot._bots['enemy'][0], bot._bots['team'][1], bot._bots['enemy'][1]]
    else:
        turn = bot.turn * 2 + 1
        teams = [bot.enemy[0], bot]
        bots = [bot._bots['enemy'][0], bot._bots['team'][0], bot._bots['enemy'][1], bot._bots['team'][1]]

    bot_was_killed = [False] * 4 # TODO

    game_state = {
       "bots": [b.position for b in bots],
       "turn": turn,
       "gameover": False, # otherwise there is no bot
       "score": [t.score for t in teams],
       "food": [t.food for t in teams],
       "walls": bot.walls,
       "round": bot.round,
       "kills": [b.kills for b in bots],
       "deaths": [b.deaths for b in bots],
       "bot_was_killed": bot_was_killed,
       "errors": [[], []],
       "fatal_errors": [[], []],
       "noise_radius": 0,
       "sight_distance": 0,
       "rnd": None,
       "team_names": [t.team_name for t in teams],
       "timeout_length": 3 # TODO
    }
    return game_state

def simulate_move(bot, pos):
    gs = bot_to_gamestate(bot)
    from .game import apply_move, prepare_bot_state
    from .player.team import make_bots

    bs = prepare_bot_state(apply_move(gs, pos))
    me = make_bots(walls=bot.walls,
                   team=bs['team'],
                   enemy=bs['enemy'],
                   round=bs['round'],
                   bot_turn=bs['bot_turn'],
                   rng=bot.random)
    return me


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
    width = max(layout['walls'])[0] + 1

    food = split_food(width, layout['food'])

    if is_blue:
        team_index = 0
        enemy_index = 1
    else:
        team_index = 1
        enemy_index = 0

    rng = random.Random(seed)

    team = {
        'bot_positions': layout['bots'][:],
        'team_index': team_index,
        'score': score[team_index],
        'kills': [0]*2,
        'deaths': [0]*2,
        'bot_was_killed' : [False]*2,
        'error_count': 0,
        'food': food[team_index],
        'name': "blue" if is_blue else "red"
    }
    enemy = {
        'bot_positions': layout['enemy'][:],
        'team_index': enemy_index,
        'score': score[enemy_index],
        'kills': [0]*2,
        'deaths': [0]*2,
        'bot_was_killed': [False]*2,
        'error_count': 0,
        'food': food[enemy_index],
        'is_noisy': [False] * len(layout['enemy']),
        'name': "red" if is_blue else "blue"
    }

    bot = make_bots(walls=layout['walls'][:],
                    team=team,
                    enemy=enemy,
                    round=round,
                    bot_turn=0,
                    rng=rng)
    return bot

