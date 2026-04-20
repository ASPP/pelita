from random import Random

from .base_utils import default_rng
from .game import SHADOW_DISTANCE, split_food
from .gamestate_filters import manhattan_dist
from .layout import BOT_N2I, initial_positions, parse_layout
from .maze_generator import generate_maze
from .team import create_homezones, make_bots

# this import is needed for backward compatibility, do not remove or you'll break
# older clients!
from .team import walls_to_graph  # isort: skip


# this is a dumbed-down version of pelita.game.run_game, useful to be exposed to the
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
          #. b y #
          #a x   #
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
              - 'walls' : set of wall coordinates for the layout
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
        A move function is a function with signature move(bot, state) -> (x, y).
        The function takes a bot object and a state and returns the next position of
        the current bot as a tuple (x, y). `state` is initially an empty dictionary.

    - Timeouts:
        As opposed to standard pelita matches, timeouts are not considered.

    """
    from .game import run_game

    # if the seed is not set explicitly, set it here
    if seed is None:
        rng = Random()
        seed = rng.randint(1, 2**31)
    else:
        rng = Random(seed)

    if layout is None:
        layout_dict = generate_maze(rng=rng)
    else:
        layout_dict = parse_layout(layout)

    game_state = run_game((blue_move, red_move), layout_dict=layout_dict,
                          max_rounds=max_rounds, rng=rng,
                          team_names=('blue', 'red'), raise_bot_exceptions=True, print_result=False)
    out = {}
    out['seed'] = seed
    out['walls'] = game_state['walls']
    out['round'] = game_state['round']
    out['layout'] = ''
    out['blue_food'] = list(game_state['food'][0])
    out['red_food'] = list(game_state['food'][1])
    out['blue_bots'] = game_state['bots'][::2]
    out['red_bots'] = game_state['bots'][1::2]
    out['blue_score'] = game_state['score'][0]
    out['red_score'] = game_state['score'][1]
    out['blue_errors'] = game_state['timeouts'][0]
    out['red_errors'] = game_state['timeouts'][1]
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


def shaded_food(pos, food, radius):
    # Get all food that is in a radius around any of pos
    # TODO: This duplicates code in update_food_age
    for pellet in food:
        if any(manhattan_dist(ghost, pellet) <= radius for ghost in pos):
            yield pellet


def setup_test_game(*, layout, is_blue=True, round=None, score=None, seed=None,
                    food=None, bots=None, is_noisy=None):
    """Setup a test game environment useful for testing move functions.

    Parameters
    ----------
    layout : str
      The layout (as a string) to play with. If None, a random
      layout of normal size will be generated.

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
        already found in the layout string. The food list will be ignored if
        layout is None.

    bots : dict{"a": (a_x,a_y), "b":(b_x,b_y), "x":(x_x,x_y), "y":(y_x,y_y)}
           dict of bot names and coordinates. The items found here  will override
           the positions found in the layout. The bots dict will be ignored if
           layout is None.

    is_noisy : dict{"a": True, "b": False, "x": True, "y": False}
              Dict of bot names and booleans for the bots' is_noisy property.


    Returns
    -------
    bot : Bot
       a Bot object suitable to be passed to a move function
    """
    rng = default_rng(seed)

    if score is None:
        score = [0, 0]

    # grab is_noisy overrides from user
    is_noisy_default = {char:False for char in BOT_N2I}
    if is_noisy is not None:
        is_noisy_default.update(is_noisy)

    is_noisy = is_noisy_default
    is_noisy_list = [is_noisy["x"], is_noisy["a"], is_noisy["y"], is_noisy["b"]]


    if layout is None:
        layout = generate_maze(rng=rng)
    else:
        layout = parse_layout(layout, food=food, bots=bots)

    bot_positions = layout['bots'][:]
    width, height = layout['shape']

    food = split_food(width, layout['food'])
    food = [list(team_food) for team_food in food]

    if is_blue:
        # We only make the first bot of each team controllable,
        # therefore the turn is only 0 or 1
        turn = 0
        score = score[:]
        shaded_food_list = [list(shaded_food(bot_positions, food[0], radius=SHADOW_DISTANCE)), []]
    else:
        turn = 1
        score = list(reversed(score))
        shaded_food_list = [[], list(shaded_food(bot_positions, food[1], radius=SHADOW_DISTANCE))]


    shape = layout['shape']
    walls = layout['walls']
    shape = layout['shape']
    graph = walls_to_graph(layout['walls'])
    initial_positions_list = initial_positions(layout['walls'], layout['shape'])
    homezone = create_homezones(layout['shape'], layout['walls'])

    bot = make_bots(bot_positions=bot_positions,
                    is_noisy=is_noisy_list,
                    walls=walls,
                    shape=shape,
                    food=food,
                    shaded_food=shaded_food_list,
                    round=round,
                    turn=turn,
                    score=score,
                    deaths=[0] * 4,
                    kills=[0] * 4,
                    bot_was_killed=[False] * 4,
                    error_count=[0] * 2,
                    initial_positions=initial_positions_list,
                    homezone=homezone,
                    team_names=["blue", "red"],
                    team_time=[0.0] * 2,
                    rng=rng,
                    graph=graph)

    return bot

