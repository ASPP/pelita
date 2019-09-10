from demo02_random import move
from pelita.utils import setup_test_game


def test_always_legal_simple_layout():
    # Given a simple layout, verify that the bot always returns a valid position,
    # independent of its initial position.
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
        # check that the position is valid
        assert next_pos in bot.legal_positions


def test_always_legal():
    # Given a random builtin layout, verify that the bot always returns a valid position
    bot = setup_test_game(layout=None, is_blue=True)
    next_pos = move(bot, {})
    assert next_pos in bot.legal_positions
