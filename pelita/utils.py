import logging
import random

import networkx
from .layout import get_layout_by_name, layout_as_str, layout_for_team, parse_layout
from .player.team import create_layout, make_bots


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

def walls_to_graph(walls):
    """Return a networkx Graph object given the walls.

    Nodes in the graph are (x,y) coordinates in the layout which are not walls.
    Edges in the graph are ((x1,y1), (x2,y2)) tuples of coordinates of two adjacent nodes."""
    graph = networkx.Graph()
    extreme = max(walls)
    width =  extreme[0] + 1
    heigth = extreme[1] + 1
    for x in range(width):
        for y in range(heigth):
            if (x, y) not in walls:
                # this is a free position, get its neighbors
                for delta_x, delta_y in ((1,0), (-1,0), (0,1), (0,-1)):
                    neighbor = (x + delta_x, y + delta_y)
                    # we don't need to check for getting neighbors out of the maze
                    # because our mazes are all surrounded by walls, i.e. our
                    # deltas will not put us out of the maze
                    if neighbor not in walls:
                        # this is a genuine neighbor, add an edge in the graph
                        graph.add_edge((x, y), neighbor)
    return graph

def load_builtin_layout(layout_name, *, is_blue=True):
    """ Loads a builtin layout with the given `layout_name` and returns a layout string.
    """
    return layout_as_str(**layout_for_team(parse_layout(get_layout_by_name(layout_name)), is_blue=is_blue))


def setup_test_game(*, layout, game=None, is_blue=True, round=None, score=None, seed=None,
                    food=None, bots=None, enemy=None, is_noisy=None):
    """Returns the first bot object given a layout.

    The returned Bot instance can be passed to a move function to test its return value.
    The layout is a string that can be passed to create_layout."""
    if game is not None:
        raise RuntimeError("Re-using an old game is not implemented yet.")

    if score is None:
        score = [0, 0]

    layout = create_layout(layout, food=food, bots=bots, enemy=enemy, is_noisy=is_noisy)
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
        'is_noisy': layout['is_noisy'],
        'name': "red" if is_blue else "blue"
    }

    bot = make_bots(walls=layout['walls'][:],
                    team=team,
                    enemy=enemy,
                    round=round,
                    bot_turn=0,
                    rng=rng)
    return bot

