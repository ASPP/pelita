from demo01_stopping import move
from utils import setup_test_game

def test_stays_there_simple_layout():
    # Given a simple layout, verify that the bot does not move, independent
    # of its initial position.
    layout="""
    ########
    #     .#
    #.1  EE#
    ########
    """
    # generate all possible locations within the maze
    all_locations = ((x, y) for x in range(1,7) for y in range(1,3))
    for loc in all_locations:
        bot = setup_test_game(layout=layout, is_blue=True, bots=[loc])
        next_pos = move(bot, {})
        # check that we did not move
        assert next_pos == bot.position

def test_stays_there_builtin_fixed_layout():
    # Using a fixed builtin layout, verify that the bot stays on its initial position
    bot = setup_test_game(layout='normal_050', is_blue=True)
    next_pos = move(bot, {})
    # check that we did not move
    assert next_pos == bot.position

def test_stays_there_builtin_random_layout():
    # Using a random builtin layout, verify that the bot stays on its initial position
    bot = setup_test_game(layout=None, is_blue=True)
    next_pos = move(bot, {})
    # check that we did not move
    assert next_pos == bot.position
