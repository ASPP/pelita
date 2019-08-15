import random

import networkx

from .layout import get_layout_by_name, layout_as_str, layout_for_team, parse_layout
from .player.team import create_layout, make_bots

def walls_to_graph(walls):
    """Return a networkx Graph object given the walls of a maze.

    Parameters
    ----------
    walls : list[(x0,y0), (x1,y1), ...]
         a list of walls coordinates

    Returns
    -------
    graph : networkx.Graph
         a networkx Graph representing the free squares in the maze and their
         connections. Note that 'free' in this context means that the corresponding
         square in the maze is not a wall (but can contain food or bots).

    Notes
    -----
    Nodes in the graph are (x,y) coordinates representing a square in the maze
    which are not walls.
    Edges in the graph are ((x1,y1), (x2,y2)) tuples of coordinates of two
    adjacent squares. Adjacent means that you can go from one square to one of
    its adjacent squares by making ore single step (up, down, left, or right).
    """
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


def setup_test_game(*, layout, is_blue=True, round=None, score=None, seed=None,
                    food=None, bots=None, enemy=None, is_noisy=None):
    """Setup a test game environment useful for testing move functions.

    Parameters
    ----------
    layout : str
          a valid layout string, like the one obtained by print(bot). For example:
              layout='''
                     ########
                     #0    .#
                     #.1  EE#
                     ########
                     '''

    is_blue : bool
           when True setups up the game assuming your bots are in the blue team,
           i.e. the team with the homezone on the left side of the maze. Otherwise
           your bots are assumed to be in the red team.

    round : int
         set the current round for the returned game state

    score : list[int, int]
         set the score for you and the enemy team. Example: [12,15] -> your score
         is 12, your enemy score is 15. If None score will be set to [0, 0]

    seed : int
        set the random number generator seed to get reproducible results if your
        move function uses the bot.random random generator

    food : list[(x0,y0), (x1,y1),...]
        list of coordinates for food pellets. The food will be added to the one
        already found in the layout string

    bots : list[(x0,y0), (x1,y1)]
        list of coordinates for your bots. These will override the positions found
        in the layout. If only one pair of coordinates is given, i.e. you pass just
        [(x0,y0)] only the position for bot '0' will be set

    enemy : list[(x0,y0), (x1,y1)]
         list of coordinates for the enemy bots. These will override the positions
         found in the layout. If only one pair of coordinates is given, i.e. you
         pass just [(x0,y0)] only the position for enemy bot '0' will be set

    is_noisy : list[bool, bool]
            list of two booleans for the enemy bots is_noisy property


    Returns
    -------
    bot : Bot
       a Bot object suitable to be passed to a move function
    """

    if score is None:
        score = [0, 0]

    layout = create_layout(layout, food=food, bots=bots, enemy=enemy, is_noisy=is_noisy)
    width = max(layout['walls'])[0] + 1

    def split_food(width, food):
        team_food = [set(), set()]
        for pos in food:
            idx = pos[0] // (width // 2)
            team_food[idx].add(pos)
        return team_food

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

