from demo03_smartrandom import move
from pelita.utils import setup_test_game

def test_legalmoves():
    # check that the only two valid moves are always returned
    # we try ten times, to test 10 different random streams
    layout="""
    ########
    #0######
    #1. .EE#
    ########
    """
    for i in range(10):
        game = setup_test_game(layout=layout, is_blue=True)
        next_move = move(0, game)
        assert next_move in ((0,1), (0,0))

def test_eat_enemy():
    # check that we indeed it a enemy when possible
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
    # check that we indeed collect food when possible
    layout="""
    ########
    #E # .##
    #1.E 0 #
    ########
    """
    game = setup_test_game(layout=layout, is_blue=True)
    next_move = move(0, game)
    assert next_move == (0,-1)

def test_no_kamikaze_back():
    # check that we escape if faced with an enemy
    layout="""
    ########
    #E ###.#
    #1.  0E#
    ########
    """
    game = setup_test_game(layout=layout, is_blue=True)
    next_move = move(0, game)
    assert next_move == (-1, 0)

def test_no_kamikaze_stop():
    # Check that we stop if escaping would kill us
    layout="""
    ########
    #  ###.#
    #1. E0E#
    ########
    """
    game = setup_test_game(layout=layout, is_blue=True)
    next_move = move(0, game)
    assert next_move == (0, 0)
