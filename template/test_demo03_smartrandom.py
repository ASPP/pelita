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
        bot = setup_test_game(layout=layout, is_blue=True)
        next_move,_ = move(bot, None)
        assert next_move in ((0,1), (0,0))

def test_eat_enemy():
    # check that we indeed eat an enemy when possible
    layout="""
    ########
    #E###.##
    #0.  1E#
    ########
    """
    bot = setup_test_game(layout=layout, is_blue=True)
    next_move, _ = move(bot, None)
    assert next_move == (0,-1)

def test_eat_food():
    # check that we indeed collect food when possible
    layout="""
    ########
    #E # .##
    #1.E 0 #
    ########
    """
    bot = setup_test_game(layout=layout, is_blue=True)
    next_move, _ = move(bot, None)
    assert next_move == (0,-1)

def test_no_kamikaze_stop():
    # Check that we stop if escaping would kill us
    layout="""
    ########
    #  ###.#
    #1. E0E#
    ########
    """
    bot = setup_test_game(layout=layout, is_blue=True)
    next_move, _ = move(bot, state)
    assert next_move == (0, 0)
