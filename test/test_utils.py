import pytest

from pelita import utils
from pelita.player import stopping_player


@pytest.mark.parametrize('is_blue', [True, False])
def test_setup_test_game(is_blue):
    # Test that is_noisy is set properly
    layout = """
    ##################
    #. ... .##.     y#
    # # #  .  .### # #
    # # ##. x .      #
    #      .   .## # #
    #a# ###.  .  # # #
    #b     .##. ... .#
    ##################
    """
    test_game = utils.setup_test_game(layout=layout, is_blue=is_blue, is_noisy={"a":False, "b":True, "x":False, "y":True})

    if is_blue:
        assert test_game.position == (1, 5)
        assert test_game.other.position == (1, 6)
        assert test_game.enemy[0].position == (8, 3)
        assert test_game.enemy[1].position == (16, 1)
    else:
        assert test_game.position == (8, 3)
        assert test_game.other.position == (16, 1)
        assert test_game.enemy[0].position == (1, 5)
        assert test_game.enemy[1].position == (1, 6)

    # load_builtin_layout loads unnoised enemies
    assert test_game.enemy[0].is_noisy is False
    assert test_game.enemy[1].is_noisy is True


@pytest.mark.parametrize('is_blue', [True, False])
def test_setup_test_game_incomplete_noisy_dict(is_blue):
    # Test that is_noisy is set properly
    layout = """
    ##################
    #. ... .##.     y#
    # # #  .  .### # #
    # # ##. x .      #
    #      .   .## # #
    #a# ###.  .  # # #
    #b     .##. ... .#
    ##################
    """
    test_game = utils.setup_test_game(layout=layout, is_blue=is_blue, is_noisy={"b":True, "y":True})
    # load_builtin_layout loads unnoised enemies
    assert test_game.enemy[0].is_noisy is False
    assert test_game.enemy[1].is_noisy is True


def test_run_background_game():
    result = utils.run_background_game(blue_move=stopping_player, red_move=stopping_player)
    result.pop('seed')
    result.pop('walls')
    result.pop('layout')
    result.pop('blue_food')
    result.pop('red_food')
    assert result == {
        'round': 300,
        'blue_bots': [(1, 13), (1, 14)],
        'red_bots': [(30, 2), (30, 1)],
        'blue_score': 0,
        'red_score': 0,
        'blue_errors': {},
        'red_errors': {},
        'blue_deaths': [0, 0],
        'red_deaths': [0, 0],
        'blue_kills': [0, 0],
        'red_kills': [0, 0],
        'blue_wins': False,
        'red_wins': False,
        'draw': True
    }

