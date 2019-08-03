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
        next_pos,_ = move(bot, None)
        assert next_pos in ((1,2), (1,1))

def test_kill_enemy():
    # check that we indeed kill an enemy when possible
    layout="""
    ########
    #E###.##
    #0.  1E#
    ########
    """
    bot = setup_test_game(layout=layout, is_blue=True)
    next_pos, _ = move(bot, None)
    assert next_pos == (1,1)

def test_eat_food():
    # check that we indeed collect food when possible
    layout="""
    ########
    #E # .##
    #1.E 0 #
    ########
    """
    bot = setup_test_game(layout=layout, is_blue=True)
    next_pos, _ = move(bot, None)
    assert next_pos == (5,1)

def test_no_kamikaze_stop():
    # Check that we stop if escaping would kill us
    layout="""
    ########
    #  ###.#
    #1. E0E#
    ########
    """
    bot = setup_test_game(layout=layout, is_blue=True)
    next_pos, _ = move(bot, None)
    assert next_pos == (5, 2)
