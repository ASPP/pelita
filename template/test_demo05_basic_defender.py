from demo05_basic_defender import move
from pelita.utils import setup_test_game

def test_kill_enemy():
    # do we eat food when it's available?
    layout="""
    ########
    #    1.#
    #.0E  E#
    ########
    """
    game = setup_test_game(layout=layout, is_blue=True)
    next_move = move(0, game)
    assert next_move == (1, 0)

def test_stop_at_the_border():
    # do we stop at the border when we reach it?
    layout="""
    ########
    #    1.#
    #. 0E E#
    ########"""
    game = setup_test_game(layout=layout, is_blue=True)
    next_move = move(0, game)
    assert next_move == (0, 0)

def test_face_the_enemy():
    # do we move along the border to face the enemy when it's still in its own
    # homezone?
    layout="""
    ########
    #  0 1.#
    #.  E E#
    ########"""
    game = setup_test_game(layout=layout, is_blue=True)
    next_move = move(0, game)
    assert next_move == (0, 1)

