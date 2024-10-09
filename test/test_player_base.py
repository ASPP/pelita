
from random import Random

from pelita.game import setup_game, run_game, play_turn
from pelita.layout import parse_layout
from pelita.player import (random_player, stopping_player, stepping_player,
                           round_based_player, speaking_player)


# some directions that are used in the tests
north = (0, -1)
south = (0, 1)
west  = (-1, 0)
east  = (1, 0)
stop  = (0, 0)

class TestSteppingPlayer:
    def test_stepping_players(self):
        test_layout = (
        """ ############
            #a  .  .  x#
            #b        y#
            ############ """)
        movements_0 = [east, east]
        movements_1 = [west, west]
        teams = [
            stepping_player(movements_0, movements_0),
            stepping_player(movements_1, movements_1)
        ]
        state = setup_game(teams, layout_dict=parse_layout(test_layout), max_rounds=2)
        assert state['bots'] == [(1, 1), (10, 1), (1, 2), (10, 2)]
        state = run_game(teams, layout_dict=parse_layout(test_layout), max_rounds=2)
        assert state['bots'] == [(3, 1), (8, 1), (3, 2), (8, 2)]

    def test_shorthand(self):
        test_layout = (
        """ ############
            #a  .  .  y#
            #b        x#
            ############ """)
        num_rounds = 5
        teams = [
            stepping_player('>v<^-', '-----'),
            stepping_player('<^>v-', '-----')
        ]
        state = setup_game(teams, layout_dict=parse_layout(test_layout), max_rounds=5)
        player0_expected_positions = [(1,1), (2,1), (2,2), (1,2), (1,1), (1, 1)]
        player1_expected_positions = [(10,2), (9,2), (9,1), (10,1), (10,2), (10, 2)]

        assert state['bots'][0] == player0_expected_positions[0]
        assert state['bots'][1] == player1_expected_positions[0]
        for i in range(1, num_rounds+1):
            for step in range(4):
                state = play_turn(state)
            assert state['bots'][0] == player0_expected_positions[i]
            assert state['bots'][1] == player1_expected_positions[i]


    def test_too_many_moves(self):
        test_layout = (
        """ ############
            #a  .  .  x#
            #b        y#
            ############ """)
        movements_0 = [east, east]
        movements_1 = [west, west]
        teams = [
            stepping_player(movements_0, movements_0),
            stepping_player(movements_1, movements_1)
        ]
        state = run_game(teams, layout_dict=parse_layout(test_layout), max_rounds=2)
        assert state['fatal_errors'] == [[], []]
        state = run_game(teams, layout_dict=parse_layout(test_layout), max_rounds=3)
        assert len(state['fatal_errors'][0])
        # TODO: check for exact turn/round of the failure


class TestRoundBasedPlayer:
    def test_round_based_players(self):
        test_layout = (
        """ ############
            #a  .  .  x#
            #b        y#
            ############ """)
        # index 0 can be ignored
        movements_0 = [None, east, east]
        movements_1_0 = {1: west, 3: west}
        movements_1_1 = {3: west}
        teams = [
            round_based_player(movements_0, movements_0),
            round_based_player(movements_1_0, movements_1_1)
        ]
        state = setup_game(teams, layout_dict=parse_layout(test_layout), max_rounds=3)
        assert state['bots'][0] == (1, 1)
        assert state['bots'][1] == (10, 1)
        assert state['bots'][2] == (1, 2)
        assert state['bots'][3] == (10, 2)

        state = run_game(teams, layout_dict=parse_layout(test_layout), max_rounds=3)
        assert state['bots'][0] == (3, 1)
        assert state['bots'][1] == (8, 1)
        assert state['bots'][2] == (3, 2)
        assert state['bots'][3] == (9, 2)

class TestRandomPlayerSeeds:
    def test_demo_players(self):
        test_layout = (
        """ ################
            #b            y#
            #              #
            #              #
            #   a      x   #
            #              #
            #              #
            #              #
            #.            .#
            ################ """)
        teams = [
            random_player,
            random_player
        ]
        state = setup_game(teams, layout_dict=parse_layout(test_layout), max_rounds=20, rng=20)
        assert state['bots'][0] == (4, 4)
        assert state['bots'][1] == (4 + 7, 4)

        state = run_game(teams, layout_dict=parse_layout(test_layout), max_rounds=20, rng=20)
        pos_left_bot = state['bots'][0]
        pos_right_bot = state['bots'][1]

        # running again to test seed:
        state = run_game(teams, layout_dict=parse_layout(test_layout), max_rounds=20, rng=20)
        assert state['bots'][0] == pos_left_bot
        assert state['bots'][1] == pos_right_bot

        # running again with other seed:
        state = run_game(teams, layout_dict=parse_layout(test_layout), max_rounds=20, rng=200)
        # most probably, either the left bot or the right bot or both are at
        # a different position
        assert not (state['bots'][0] == pos_left_bot and state['bots'][1] == pos_right_bot)

    def test_random_seeds(self):
        test_layout = (
        """ ################
            #              #
            #              #
            #              #
            #   a      x   #
            #   b      y   #
            #              #
            #              #
            #.            .#
            ################ """)
        def init_rng_players():
            player_rngs = []
            def rng_test(bot, state):
                player_rngs.append(bot.random)
                return bot.position, state
            team = [
                rng_test,
                rng_test
            ]
            return team, player_rngs

        team0, player_rngs0 = init_rng_players()
        state = setup_game(team0, layout_dict=parse_layout(test_layout), max_rounds=5, rng=20)
        # play two steps
        play_turn(play_turn(state))
        assert len(player_rngs0) == 2
        # generate some random numbers for each player
        random_numbers0 = [rng.randint(0, 10000) for rng in player_rngs0]
        # teams should have generated a different number
        assert random_numbers0[0] != random_numbers0[1]

        team1, player_rngs1 = init_rng_players()
        state = setup_game(team1, layout_dict=parse_layout(test_layout), max_rounds=5, rng=20)
        # play two steps
        play_turn(play_turn(state))
        assert len(player_rngs1) == 2
        # generate some random numbers for each player
        random_numbers1 = [rng.randint(0, 10000) for rng in player_rngs1]
        # teams should have generated the same numbers as before
        assert random_numbers0 == random_numbers1

        # now, use a different seed
        team2, player_rngs2 = init_rng_players()
        state = setup_game(team2, layout_dict=parse_layout(test_layout), max_rounds=5, rng=200)
        # play two steps
        play_turn(play_turn(state))
        assert len(player_rngs2) == 2
        # generate some random numbers for each player
        random_numbers2 = [rng.randint(0, 10000) for rng in player_rngs0]
        # teams should have generated different numbers than before
        assert random_numbers0 != random_numbers2


def test_speaking_player():
    test_layout = (
    """ ############
        #ab#.  .#yx#
        ############ """)
    teams = [
        speaking_player,
        random_player
    ]
    state = run_game(teams, layout_dict=parse_layout(test_layout), max_rounds=1)
    assert state["say"][0].startswith("Going")
    assert state["say"][1] == ""

