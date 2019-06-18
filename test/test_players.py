import pytest

from pelita.game import run_game
from pelita.layout import parse_layout
from pelita.player import nq_random_player, SANE_PLAYERS


class TestNQRandom_Player:
    def test_demo_players(self):
        test_layout = (
        """ ############
            #0#.   .# 1#
            ###.   .####
            #2#.   .# 3#
            ############ """)
        teams = [
            nq_random_player,
            nq_random_player
        ]
        state = run_game(teams, layout_dict=parse_layout(test_layout), max_rounds=1)
        assert state['bots'][0] == (1, 1)
        assert state['bots'][1] == (9, 1)

    def test_path(self):
        test_layout = (
        """ ############
            #  . # .# ##
            # ## #  # ##
            #0#.   .##1#
            ###.   .####
            #2#.   .# 3#
            ############ """)
        teams = [
            nq_random_player,
            nq_random_player
        ]
        state = run_game(teams, layout_dict=parse_layout(test_layout), max_rounds=7)
        assert state['bots'][0] == (4, 3)
        assert state['bots'][1] == (10, 3)


@pytest.mark.parametrize('player', SANE_PLAYERS)
def test_players(player):
    # Simple checks that the players are running to avoid API discrepancies
    test_layout = (
    """ ############
        #2 . # . 3##
        # ## #    ##
        # ## #  # ##
        # ## #  # ##
        #    #  # ##
        #0#.   .  1#
        ############ """)
    
    teams = [
        player,
        nq_random_player
    ]
    state = run_game(teams, layout_dict=parse_layout(test_layout), max_rounds=20)
    assert state['gameover']
    # ensure that all test players ran correctly
    assert state['fatal_errors'] == [[], []]
    # our test players should never return invalid moves
    assert state['errors'] == [{}, {}]

