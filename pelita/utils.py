import logging
import random

import networkx

from .layout import get_random_layout, get_layout_by_name, parse_layout
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

# this is a dumbed-down version of pelita.game.run_game, useful t be exposed to the
# users to run background games. It hides most of the parameters of run_game which
# are not relevant to the user in this setup and reformats the rest so that we
# don't leak internal implementation details and indices.
def run_background_game(*, blue_move, red_move, layout=None, max_rounds=300, seed=None):
    """Run a pelita match.

    Parameters
    ----------
    blue_move : function
             the move function that will be used by the blue team

    red_move : function
             the move function that will be used by the red team

    layout : str
          specify the layout of the maze to play with. If None, a built-in
          layout of normal size will be chosen at random. If specified it will
          be interpreted as the name of a built-in layout, e.g. 'normal_083'.
          You can also pass a layout string as in:
          '''
          ########
          #. 1 E #
          #0 E   #
          ########
          '''

    max_rounds : int
              maximum number of rounds to play before the game is over. Default: 300.

    seed : int
        seed used to initialize the random number generator.


    Returns
    -------
    game_state : dict
              the final game state as a dictionary. Dictionary keys are:
              - 'walls' : list of walls coordinates for the layout
              - 'layout' : the name of the used layout
              - 'round' : the round at which the game was over
              - 'draw' : True if the game ended in a draw
              - 'blue_food' : list of food coordinates for the blue team. Note that
                              this can be empty if the red team has eaten all the
                              blue team's food
             - 'red_food' : list of food coordinates for the red team
             - 'blue_bots' : list of coordinates for the blue team's bots
             - 'red_bots' : list of coordinates for the red team's bots
             - 'blue_score' : score of the blue team
             - 'red_score' : score of the red team
             - 'blue_errors' : a dictionary collecting non-fatal errors for the
                               blue team
             - 'red_errors' : a dictionary collecting non-fatal errors for the
                              red team
             - 'blue_deaths' : a list with the number of times each bot in the blue
                               team has been killed
             - 'red_deaths' : a list with the number of times each bot in the red
                              team has been killed
             - 'blue_kills' : a list with the number of times each bot in the blue
                              team has killed enemy bots
             - 'red_kills' : a list with the number of times each bot in the red
                              team has killed enemy bots
             - 'blue_wins' : True if the blue team wins
             - 'red_wins' : True if the red team wins

    Notes
    -----
    - Move functions:
        A move function is a function with signature move(bot, state) -> (x, y), state
        the function takes a bot object and a state and returns the next position of
        the current bot as a tuple (x, y) and state. `state` can be an arbitrary
        Python object, None by default

    - Timeouts:
        As opposed to standard pelita matches, timeouts are not considered.

    """
    from . import game
    from .game import setup_game, play_turn, prepare_viewer_state

    # prepare layout argument to be passed to pelita.game.run_game
    if layout is None:
        layout_name, layout_str = get_random_layout(size='normal')
        layout_dict = parse_layout(layout_str, allow_enemy_chars=False)
    else:
        try:
            # check if this is a built-in layout
            layout_name = layout
            layout_str = get_layout_by_name(layout)
            layout_dict = parse_layout(layout_str, allow_enemy_chars=False)
        except ValueError:
            # OK, then it is a (user-provided, i.e. with 'E's) layout string
            layout_str = layout
            layout_name = '<string>'
            layout_dict = parse_layout(layout_str, allow_enemy_chars=True)

    game_state = setup_game((blue_move, red_move), layout_dict=layout_dict,
                            layout_name=layout_name, max_rounds=max_rounds, seed=seed,
                            team_names=('blue', 'red'), allow_exceptions=True)
    replay = []
    while not game_state['gameover']:
        replay.append((game_state['round'], game_state['turn'], prepare_viewer_state(game_state)))
        game_state = play_turn(game_state)

    out = {}
    out['walls'] = game_state['walls']
    out['round'] = game_state['round']
    out['layout'] = layout_name
    out['blue_food'] = list(game_state['food'][0])
    out['red_food'] = list(game_state['food'][1])
    out['blue_bots'] = game_state['bots'][::2]
    out['red_bots'] = game_state['bots'][1::2]
    out['blue_score'] = game_state['score'][0]
    out['red_score'] = game_state['score'][1]
    out['blue_errors'] = game_state['errors'][0]
    out['red_errors'] = game_state['errors'][1]
    out['blue_deaths'] = game_state['deaths'][::2]
    out['red_deaths'] = game_state['deaths'][1::2]
    out['blue_kills'] = game_state['kills'][::2]
    out['red_kills'] = game_state['kills'][1::2]
    out['blue_wins'], out['red_wins'], out['draw'] = False, False, False
    if game_state['whowins'] == 0:
        out['blue_wins'] = True
    elif game_state['whowins'] == 1:
        out['red_wins'] = True
    else:
        out['draw'] = True

    return out, replay

def replay_background_game(replay_list, viewer='tk'):
    from . import game
    from .game import setup_game, play_turn, prepare_viewer_state

    viewer_state = game.setup_viewers([viewer], options={})
    if game.controller_exit(viewer_state, await_action='set_initial'):
        return

    for round, turn, state in replay_list:
        for viewer in viewer_state['viewers']:
            viewer.show_state(state)
        if game.controller_exit(viewer_state):
            break


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

