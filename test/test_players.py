from random import Random

import pytest

from pelita.game import run_game
from pelita.layout import parse_layout
from pelita.player import (SANE_PLAYERS, food_eating_player, nq_random_player,
                           random_explorer_player, smart_eating_player,
                           smart_random_player)
from pelita.utils import setup_test_game


class TestNQRandom_Player:
    def test_demo_players(self):
        test_layout = (
        """ ############
            #a#.   .# x#
            ###.   .####
            #b#.   .# y#
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
            #a#.   .##x#
            ###.   .####
            #b#.   .# y#
            ############ """)
        teams = [
            nq_random_player,
            nq_random_player
        ]
        state = run_game(teams, layout_dict=parse_layout(test_layout), max_rounds=7)
        assert state['bots'][0] == (4, 3)
        assert state['bots'][1] == (10, 3)

    def test_only_move_forward(self):
        # test that the bot only moves forward
        layout="""
        ########
        #y #.###
        #b.x a #
        ########
        """
        bot = setup_test_game(layout=layout, is_blue=True)
        bot.track = [(6, 2), (5, 2)]
        assert bot.position == (5, 2)
        next_pos = nq_random_player(bot, {})
        assert next_pos == (4, 2)

    def test_only_move_unless_blocked(self):
        # test that the bot only moves forward
        layout="""
        ########
        #y #.###
        #b.x#a #
        ########
        """
        bot = setup_test_game(layout=layout, is_blue=True)
        bot.track = [(6, 2), (5, 2)]
        assert bot.position == (5, 2)
        next_pos = nq_random_player(bot, {})
        assert next_pos == (6, 2)


class TestRandomExplorerPlayers:
    def test_goes_to_unvisited(self):
        layout="""
        ########
        #y # .##
        #b.x a #
        ########
        """
        bot = setup_test_game(layout=layout, is_blue=True)
        state = {0: {'visited': [(5, 1), (4, 1), (4, 2), (3, 2), (2, 2), (1, 2)]}}
        assert bot.position == (5, 2)
        next_pos = random_explorer_player(bot, state)
        assert next_pos == (6, 2)

    def test_goes_to_least_recently_visited(self):
        layout="""
        ########
        #y # .##
        #b.x a #
        ########
        """
        bot = setup_test_game(layout=layout, is_blue=True)
        state = {0: {'visited': [(6, 2), (5, 2), (5, 1), (4, 1), (4, 2), (3, 2), (2, 2), (1, 2)]}}
        assert bot.position == (5, 2)
        # check that we have already visited all legal positions
        assert all(pos in state[0]['visited'] for pos in bot.legal_positions)
        next_pos = random_explorer_player(bot, state)
        assert next_pos == (4, 2)


class TestSmartRandomPlayer:
    def test_legalmoves(self):
        # check that the only two valid moves are always returned
        # we try ten times, to test 10 different random streams
        layout="""
        ########
        #a######
        #b. .xy#
        ########
        """
        for i in range(10):
            bot = setup_test_game(layout=layout, is_blue=True)
            next_pos = smart_random_player(bot, {})
            assert next_pos in ((1,2), (1,1))

    def test_kill_enemy(self):
        # check that we indeed kill an enemy when possible
        layout="""
        ########
        #x###.##
        #a.  by#
        ########
        """
        bot = setup_test_game(layout=layout, is_blue=True)
        next_pos = smart_random_player(bot, {})
        assert next_pos == (1,1)

    def test_eat_food(self):
        # check that we indeed collect food when possible
        layout="""
        ########
        #y # .##
        #b.x a #
        ########
        """
        bot = setup_test_game(layout=layout, is_blue=True)
        next_pos = smart_random_player(bot, {})
        assert next_pos == (5,1)

    def test_no_kamikaze_stop(self):
        # Check that we stop if escaping would kill us
        layout="""
        ########
        #  ###.#
        #b. xay#
        ########
        """
        bot = setup_test_game(layout=layout, is_blue=True)
        next_pos = smart_random_player(bot, {})
        assert next_pos == (5, 2)


class TestFoodEatingPlayer:
    def test_legalmoves(self):
        # check that the only two valid moves are returned
        layout="""
        ########
        #a######
        #b. .xy#
        ########
        """
        bot = setup_test_game(layout=layout, is_blue=True)
        next_pos = food_eating_player(bot, {})
        assert next_pos in ((1,2), (1,1))

    def test_eat_food(self):
        # check that we eat the last food when adjacent
        layout="""
        ########
        #x  a.##
        # .  by#
        ########
        """
        bot = setup_test_game(layout=layout, is_blue=True)
        next_pos = food_eating_player(bot, {})
        assert next_pos == (5,1)

    def test_move_towards_food(self):
        # check that we move closer to the food
        layout="""
        ########
        #y a .##
        #b.x   #
        ########
        """
        bot = setup_test_game(layout=layout, is_blue=True)
        next_pos = food_eating_player(bot, {})
        assert next_pos == (4,1)

    def test_move_towards_next_food(self):
        # check that we move closer to the food in the next_food key,
        # even though another food is closer
        layout="""
        ########
        #y   .##
        #      #
        # .. a #
        #x   . #
        # .b   #
        ########
        """
        bot = setup_test_game(layout=layout, is_blue=True)
        next_pos = food_eating_player(bot, {0: {'next_food': (5, 1)}})
        assert next_pos == (5, 2)

    def test_will_do_kamikaze(self):
        # check that we eat the last food when adjacent
        layout="""
        ########
        #x  a.##
        # .  b #
        ########
        """
        bot = setup_test_game(layout=layout, is_blue=True, bots={'y': (5, 1)})
        next_pos = food_eating_player(bot, {})
        assert next_pos == (5,1)

class TestSmartEatingPlayer:
    def test_legalmoves(self):
        # check that the only two valid moves are returned
        layout="""
        ########
        #a######
        #b. .xy#
        ########
        """
        bot = setup_test_game(layout=layout, is_blue=True)
        next_pos = smart_eating_player(bot, {})
        assert next_pos in ((1,2), (1,1))

    def test_eat_food(self):
        # check that we eat the last food when adjacent
        layout="""
        ########
        #x  a.##
        # .  by#
        ########
        """
        bot = setup_test_game(layout=layout, is_blue=True)
        next_pos = smart_eating_player(bot, {})
        assert next_pos == (5,1)

    def test_move_towards_food(self):
        # check that we move closer to the food
        layout="""
        ########
        #y a .##
        #b.x   #
        ########
        """
        bot = setup_test_game(layout=layout, is_blue=True)
        next_pos = smart_eating_player(bot, {})
        assert next_pos == (4,1)

    def test_move_towards_next_food(self):
        # check that we move closer to the food in the next_food key,
        # even though another food is closer
        layout="""
        ########
        #y   .##
        #      #
        # .. a #
        #x   . #
        # .b   #
        ########
        """
        bot = setup_test_game(layout=layout, is_blue=True)
        next_pos = smart_eating_player(bot, {0: {'next_food': (5, 1)}})
        assert next_pos == (5, 2)

    def test_will_not_do_kamikaze(self):
        # check that we eat the last food when adjacent
        layout="""
        ########
        #x  a.##
        # .  b #
        ########
        """
        bot = setup_test_game(layout=layout, is_blue=True, bots={'y': (5, 1)})
        next_pos = smart_eating_player(bot, {})
        assert next_pos == (4,1)

@pytest.mark.parametrize('player', SANE_PLAYERS)
def test_players(player):
    # Simple checks that the players are running to avoid API discrepancies
    test_layout = (
    """ ############
        #b . # . y##
        # ## #    ##
        # ## #  # ##
        # ## #  # ##
        #    #  # ##
        #a#.   .  x#
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

