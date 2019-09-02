import random

import networkx

from .player.team import make_bots

def walls_to_graph(walls):
    """Return a networkx Graph object given the walls of a maze.

    Parameters
    ----------
    walls : list[(x0,y0), (x1,y1), ...]
         a list of wall coordinates

    Returns
    -------
    graph : networkx.Graph
         a networkx Graph representing the free squares in the maze and their
         connections. Note that 'free' in this context means that the corresponding
         square in the maze is not a wall (but can contain food or bots).

    Notes
    -----
    Nodes in the graph are (x,y) coordinates representing squares in the maze
    which are not walls.
    Edges in the graph are ((x1,y1), (x2,y2)) tuples of coordinates of two
    adjacent squares. Adjacent means that you can go from one square to one of
    its adjacent squares by making ore single step (up, down, left, or right).
    """
    graph = networkx.Graph()
    extreme = max(walls)
    width =  extreme[0] + 1
    height = extreme[1] + 1
    for x in range(width):
        for y in range(height):
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

def _parse_layout_arg(*, layout=None, food=None, bots=None, enemy=None,
                         is_noisy=None, is_blue=True, agnostic=True):
    from .layout import (get_random_layout, get_layout_by_name, get_available_layouts,
                         parse_layout, layout_for_team, layout_agnostic)

    # prepare layout argument to be passed to pelita.game.run_game
    if layout is None:
        layout_name, layout_str = get_random_layout(size='normal')
        layout_dict = parse_layout(layout_str, allow_enemy_chars=False)
        if not agnostic:
            layout_dict = layout_for_team(layout_dict, is_blue=is_blue)
    elif layout in get_available_layouts(size='all'):
        # check if this is a built-in layout
        layout_name = layout
        layout_str = get_layout_by_name(layout)
        layout_dict = parse_layout(layout_str, allow_enemy_chars=False)
        if not agnostic:
            layout_dict = layout_for_team(layout_dict, is_blue=is_blue)
    else:
        # OK, then it is a (user-provided, i.e. with 'E's) layout string
        layout_str = layout
        layout_name = '<string>'
        # be strict and complain if the layout does not contain two bots and two enemies
        layout_dict = parse_layout(layout_str, food=food, bots=bots, enemy=enemy, strict=True,
                                   is_noisy=is_noisy, is_blue=is_blue, allow_enemy_chars=True)
        if agnostic:
            layout_dict = layout_agnostic(layout_dict)

    return layout_dict, layout_name


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
              - 'seed' : the seed used to initialize the random number generator
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
    from .game import run_game

    # if the seed is not set explicitly, set it here
    if seed is None:
        seed = random.randint(1, 2**31)
        random.seed(seed)

    layout_dict, layout_name = _parse_layout_arg(layout=layout, agnostic=True)

    game_state = run_game((blue_move, red_move), layout_dict=layout_dict,
                          layout_name=layout_name, max_rounds=max_rounds, seed=seed,
                          team_names=('blue', 'red'), allow_exceptions=True, print_result=False)
    out = {}
    out['seed'] = seed
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

    return out


def setup_test_game(*, layout, is_blue=True, round=None, score=None, seed=None,
                    food=None, bots=None, enemy=None, is_noisy=None):
    """Setup a test game environment useful for testing move functions.

    Parameters
    ----------
    layout : str
      specify the layout of the maze to play with. If None, a built-in
      layout of normal size will be chosen at random. If specified it will
      be interpreted as the name of a built-in layout, e.g. 'normal_083'.
      You can also pass a layout string like the ones obtained by print(bot). For
      example:
      layout = '''
               ########
               #. 1 E #
               #0 E   #
               ########
               '''

    is_blue : bool
           when True, sets up up the game assuming your bots are in the blue team,
           i.e. the team with the homezone on the left side of the maze. When False,
           your bots are assumed to be in the red team.

    round : int
         set the current round for the returned game state

    score : list[int, int]
         set the score for you and the enemy team. Example: [12,15] -> your score
         is 12, your enemy score is 15. If None, score will be set to [0, 0]

    seed : int
        set the random number generator seed to get reproducible results if your
        move function uses the bot.random random generator

    food : list[(x0,y0), (x1,y1),...]
        list of coordinates for food pellets. The food will be added to the one
        already found in the layout string

    bots : list[(x0,y0), (x1,y1)]
        list of coordinates for your bots. These will override the positions found
        in the layout. If only one pair of coordinates is given, i.e. you pass just
        [(x0,y0)], only the position for bot '0' will be overridden

    enemy : list[(x0,y0), (x1,y1)]
         list of coordinates for the enemy bots. These will override the positions
         found in the layout. If only one pair of coordinates is given, i.e. you
         pass just [(x0,y0)], only the position for enemy bot '0' will be overridden

    is_noisy : list[bool, bool]
            list of two booleans for the enemy bots’ is_noisy property


    Returns
    -------
    bot : Bot
       a Bot object suitable to be passed to a move function
    """

    if score is None:
        score = [0, 0]

    layout, layout_name = _parse_layout_arg(layout=layout, is_blue=is_blue,
                               food=food, bots=bots, enemy=enemy,
                               is_noisy=is_noisy, agnostic=False)

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

