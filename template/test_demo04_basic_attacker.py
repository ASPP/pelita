from demo04_basic_attacker import move
from utils import setup_test_game

def test_eat_food():
    # do we eat food when it's available?
    layout="""
    ########
    #    0.#
    #.1  EE#
    ########
    """
    bot = setup_test_game(layout=layout, is_blue=True)
    next_move, _ = move(bot, None)
    assert next_move == (6, 1)

def test_no_kamikaze():
    # do we avoid enemies when they can kill us?
    layout="""
    ########
    #    E.#
    #.1  0E#
    ########
    """
    bot = setup_test_game(layout=layout, is_blue=True)
    next_move, _ = move(bot, None)
    assert next_move == (4, 2) or next_move == (5, 2)

def test_do_not_step_on_enemy():
    # check that we don't step back on an enemy when we are fleeing
    layout="""
    ########
    #    E.#
    #.1 #0E#
    ########
    """
    bot = setup_test_game(layout=layout, is_blue=True)
    next_move, _ = move(bot, None)
    assert next_move == (5, 2)

