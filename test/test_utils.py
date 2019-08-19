import pytest

from textwrap import dedent

from pelita import utils

@pytest.mark.parametrize('is_blue', [True, False])
def test_setup_test_game(is_blue):
    layout = utils.load_builtin_layout('small_001', is_blue=is_blue)
    test_game = utils.setup_test_game(layout=layout, is_blue=is_blue)

    if is_blue:
        assert test_game.position == (1, 5)
        assert test_game.other.position == (1, 6)
        assert test_game.enemy[0].position == (16, 1)
        assert test_game.enemy[1].position == (16, 2)
    else:
        assert test_game.position == (16, 2)
        assert test_game.other.position == (16, 1)
        assert test_game.enemy[0].position == (1, 5)
        assert test_game.enemy[1].position == (1, 6)

    # load_builtin_layout loads unnoised enemies
    assert test_game.enemy[0].is_noisy is False
    assert test_game.enemy[1].is_noisy is False


@pytest.mark.parametrize('is_blue', [True, False])
def test_setup_test_game(is_blue):
    # Test that is_noisy is set properly
    layout = """
    ##################
    #. ... .##.     ?#
    # # #  .  .### # #
    # # ##. E .      #
    #      .   .## # #
    #0# ###.  .  # # #
    #1     .##. ... .#
    ##################
    """
    test_game = utils.setup_test_game(layout=layout, is_blue=is_blue)

    assert test_game.position == (1, 5)
    assert test_game.other.position == (1, 6)
    assert test_game.enemy[0].position == (8, 3)
    assert test_game.enemy[1].position == (16, 1)

    # load_builtin_layout loads unnoised enemies
    assert test_game.enemy[0].is_noisy is False
    assert test_game.enemy[1].is_noisy is True


