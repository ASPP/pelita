from .demo_smartrandom import move
from pelita.utils import setup_test_game

def test_legalmoves():
    layout="""
    ########
    #0######
    #1. .EE#
    ########
    """
    # check that the only valid move is always returned
    # we try ten times, to test 10 different random streams
    for i in range(10):
        game = setup_test_game(layout=layout, is_blue=True)
        next_move = move(0, game)
        assert next_move == (0,1)

def test_eat_enemy():
    layout="""
    ########
    #E###.##
    #0.  1E#
    ########
    """
    game = setup_test_game(layout=layout, is_blue=True)
    next_move = move(0, game)
    assert next_move == (0,-1)

def test_eat_food():
    layout="""
    ########
    #E # .##
    #1.E 0 #
    ########
    """
    game = setup_test_game(layout=layout, is_blue=True)
    next_move = move(0, game)
    assert next_move == (0,-1)

def test_no_kamikaze_stop():
    layout="""
    ########
    #  ###.#
    #1. E0E#
    ########
    """
    game = setup_test_game(layout=layout, is_blue=True)
    next_move = move(0, game)
    assert next_move == (0, 0)

def test_no_kamikaze_back():
    layout="""
    ########
    #E ###.#
    #1.  0E#
    ########
    """
    game = setup_test_game(layout=layout, is_blue=True)
    next_move = move(0, game)
    assert next_move == (-1, 0)

