import pytest
import unittest

import random
import time

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


@pytest.mark.xfail(reason="Tests for convenience functions on Bot/AbstractPlayer are missing")
class TestAbstractPlayer:
    def assertUniversesEqual(self, uni1, uni2):
        assert uni1 == uni2, '\n' + uni1.pretty + '\n' + uni2.pretty

    def assertUniversesNotEqual(self, uni1, uni2):
        assert uni1 != uni2, '\n' + uni1.pretty + '\n' + uni2.pretty

    def test_convenience(self):

        test_layout = (
        """ ##################
            #0#.  .  # .     #
            #2#####    ####1 #
            #     . #  .  #3##
            ################## """)

        player_0 = StoppingPlayer()
        player_1 = SteppingPlayer('^<')
        player_2 = StoppingPlayer()
        player_3 = StoppingPlayer()
        teams = [
            SimpleTeam(player_0, player_2),
            SimpleTeam(player_1, player_3)
        ]
        game_master = GameMaster(test_layout, teams, 4, 2, noise=False)
        universe = datamodel.CTFUniverse._from_json_dict(game_master.game_state)
        game_master.set_initial()

        assert universe.bots[0] == player_0.me
        assert universe.bots[1] == player_1.me
        assert universe.bots[2] == player_2.me
        assert universe.bots[3] == player_3.me

        assert universe == player_1.current_uni
        assert [universe.bots[0]] == player_2.other_team_bots
        assert [universe.bots[1]] == player_3.other_team_bots
        assert [universe.bots[2]] == player_0.other_team_bots
        assert [universe.bots[3]] == player_1.other_team_bots
        assert [universe.bots[i] for i in (0, 2)] == player_0.team_bots
        assert [universe.bots[i] for i in (1, 3)] == player_0.enemy_bots
        assert [universe.bots[i] for i in (1, 3)] == player_1.team_bots
        assert [universe.bots[i] for i in (0, 2)] == player_1.enemy_bots
        assert [universe.bots[i] for i in (0, 2)] == player_2.team_bots
        assert [universe.bots[i] for i in (1, 3)] == player_2.enemy_bots
        assert [universe.bots[i] for i in (1, 3)] == player_3.team_bots
        assert [universe.bots[i] for i in (0, 2)] == player_3.enemy_bots

        assert player_1.current_pos == (15, 2)
        assert player_1.initial_pos == (15, 2)
        assert universe.bots[1].current_pos == (15, 2)
        assert universe.bots[1].initial_pos == (15, 2)

        assert universe.teams[0] == player_0.team
        assert universe.teams[0] == player_2.team
        assert universe.teams[1] == player_1.team
        assert universe.teams[1] == player_3.team

        assert universe.teams[1] == player_0.enemy_team
        assert universe.teams[1] == player_2.enemy_team
        assert universe.teams[0] == player_1.enemy_team
        assert universe.teams[0] == player_3.enemy_team

        unittest.TestCase().assertCountEqual(player_0.enemy_food, universe.enemy_food(player_0.team.index))
        unittest.TestCase().assertCountEqual(player_1.enemy_food, universe.enemy_food(player_1.team.index))
        unittest.TestCase().assertCountEqual(player_2.enemy_food, universe.enemy_food(player_2.team.index))
        unittest.TestCase().assertCountEqual(player_3.enemy_food, universe.enemy_food(player_3.team.index))

        unittest.TestCase().assertCountEqual(player_0.team_food, universe.team_food(player_0.team.index))
        unittest.TestCase().assertCountEqual(player_1.team_food, universe.team_food(player_1.team.index))
        unittest.TestCase().assertCountEqual(player_2.team_food, universe.team_food(player_2.team.index))
        unittest.TestCase().assertCountEqual(player_3.team_food, universe.team_food(player_3.team.index))

        assert {(0, 1): (1, 2), (0, 0): (1, 1)} == \
                player_0.legal_directions
        assert {(0, 1): (15, 3), (0, -1): (15, 1), (0, 0): (15, 2),
                          (1, 0): (16, 2)} == \
                player_1.legal_directions
        assert {(0, 1): (1, 3), (0, -1): (1, 1), (0, 0): (1, 2)} == \
                player_2.legal_directions
        assert {(0, -1): (15, 2), (0, 0): (15, 3)} == \
                player_3.legal_directions

        assert player_1.current_state["round_index"] == None
        assert player_1.current_state["bot_id"] == None

        game_master.play_round()
        universe = datamodel.CTFUniverse._from_json_dict(game_master.game_state)

        assert player_1.current_pos == (15, 2)
        assert player_1.previous_pos == (15, 2)
        assert player_1.initial_pos == (15, 2)
        assert player_1.current_state["round_index"] == 0
        assert player_1.current_state["bot_id"] == 1
        assert universe.bots[1].current_pos == (15, 1)
        assert universe.bots[1].initial_pos == (15, 2)
        self.assertUniversesEqual(player_1.current_uni, player_1.universe_states[-1])

        game_master.play_round()
        universe = datamodel.CTFUniverse._from_json_dict(game_master.game_state)

        assert player_1.current_pos == (15, 1)
        assert player_1.previous_pos == (15, 2)
        assert player_1.initial_pos == (15, 2)
        assert player_1.current_state["round_index"] == 1
        assert player_1.current_state["bot_id"] == 1
        assert universe.bots[1].current_pos == (14, 1)
        assert universe.bots[1].initial_pos == (15, 2)
        self.assertUniversesNotEqual(player_1.current_uni,
                                     player_1.universe_states[-2])

    def test_time_spent(self):
        class TimeSpendingPlayer(AbstractPlayer):
            def get_move(self):
                time_spent_begin = self.time_spent()

                sleep_time = 0.1
                time.sleep(sleep_time)

                time_spent_end = self.time_spent()

                assert 0 <= time_spent_begin < time_spent_end

                time_diff = abs(time_spent_begin + sleep_time - time_spent_end)
                delta = 0.05
                assert time_diff < delta
                return stop

        test_layout = (
        """ ############
            #0 #.  .# 1#
            ############ """)
        team = [
            SimpleTeam(TimeSpendingPlayer()),
            SimpleTeam(RandomPlayer())
        ]
        gm = GameMaster(test_layout, team, 2, 1)
        gm.play()

    def test_rnd(self):
        class RndPlayer(AbstractPlayer):
            def set_initial(self):
                original_seed = self.current_state["seed"]
                original_rand = self.rnd.randint(10, 100)
                assert 10 <= original_rand <= 100

                # now check
                test_rnd = random.Random(original_seed + self._index)
                assert test_rnd.randint(10, 100) == original_rand

            def get_move(self):
                assert 10 <= self.rnd.randint(10, 100) <= 100
                return datamodel.stop


        class SeedTestingPlayer(AbstractPlayer):
            def __init__(self):
                # must be initialised before set_initial is called
                self.seed_offset = 120

            def set_initial(self):
                original_seed = self.current_state["seed"]
                original_rand = self.rnd.randint(0, 100)

                # now check
                test_rnd = random.Random(original_seed + self.seed_offset)
                assert test_rnd.randint(0, 100) == original_rand

            def get_move(self):
                assert 10 <= self.rnd.randint(10, 100) <= 100
                return datamodel.stop

        test_layout = (
        """ ############
            #02#.  .#31#
            ############ """)
        teams = [
            SimpleTeam(RndPlayer(), SeedTestingPlayer()),
            SimpleTeam(SeedTestingPlayer(), RndPlayer())
        ]
        gm = GameMaster(test_layout, teams, 4, 1)
        gm.play()

    def test_simulate_move(self):
        test_layout = (
            """ ############
                #  #.1 .#  #
                #  #.03.#  #
                #2  .  .   #
                ############ """)

        p0 = StoppingPlayer()
        p1 = StoppingPlayer()
        p2 = StoppingPlayer()
        p3 = StoppingPlayer()

        team = [
            SimpleTeam(p0, p2),
            SimpleTeam(p1, p3)
        ]
        gm = GameMaster(test_layout, team, 4, 5)
        gm.set_initial()

        sim_uni, sim_state = p0.simulate_move(datamodel.stop)
        assert sim_state == {
            'bot_destroyed': [],
            'bot_moved': [{'bot_id': 0, 'new_pos': (5, 2), 'old_pos': (5, 2)}],
            'food_eaten': []
        }
        assert sim_uni.maze == p0.current_uni.maze
        assert sim_uni == p0.current_uni
        assert sim_uni is not p0.current_uni

        sim_uni, sim_state = p0.simulate_move(datamodel.north)
        assert sim_state == {
            'bot_destroyed': [{'bot_id': 1, 'destroyed_by': 0}],
            'bot_moved': [{'bot_id': 0, 'new_pos': (5, 1), 'old_pos': (5, 2)},
                          {'bot_id': 0, 'new_pos': (5, 1), 'old_pos': (5, 1)}],
            'food_eaten': []
        }
        assert sim_uni.maze == p0.current_uni.maze
        assert sim_uni != p0.current_uni

        sim_uni, sim_state = p0.simulate_move(datamodel.east)
        assert sim_state == {
            'bot_destroyed': [{'bot_id': 0, 'destroyed_by': 3}],
            'bot_moved': [{'bot_id': 0, 'new_pos': (6, 2), 'old_pos': (5, 2)},
                          {'bot_id': 0, 'new_pos': (5, 2), 'old_pos': (6, 2)}],
            'food_eaten': []
        }
        sim_uni, sim_state = p0.simulate_move(datamodel.south)
        assert sim_state == {
            'bot_destroyed': [],
            'bot_moved': [{'bot_id': 0, 'new_pos': (5, 3), 'old_pos': (5, 2)}],
            'food_eaten': []
        }
        sim_uni, sim_state = p0.simulate_move(datamodel.west)
        assert sim_state == {
            'bot_destroyed': [],
            'bot_moved': [{'bot_id': 0, 'new_pos': (4, 2), 'old_pos': (5, 2)}],
            'food_eaten': []
        }

        with pytest.raises(datamodel.IllegalMoveException):
            assert p1.simulate_move(datamodel.north)
        sim_uni, sim_state = p1.simulate_move(datamodel.east)
        assert sim_state == {
            'bot_destroyed': [],
            'bot_moved': [{'bot_id': 1, 'new_pos': (6, 1), 'old_pos': (5, 1)}],
            'food_eaten': []
        }
        sim_uni, sim_state = p1.simulate_move(datamodel.south)
        assert sim_state == {
            'bot_destroyed': [{'bot_id': 1, 'destroyed_by': 0}],
            'bot_moved': [{'bot_id': 1, 'new_pos': (5, 2), 'old_pos': (5, 1)},
                          {'bot_id': 1, 'new_pos': (5, 1), 'old_pos': (5, 2)}],
            'food_eaten': []
        }
        sim_uni, sim_state = p1.simulate_move(datamodel.west)
        assert sim_state == {
            'bot_destroyed': [],
            'bot_moved': [{'bot_id': 1, 'new_pos': (4, 1), 'old_pos': (5, 1)}],
            'food_eaten': [{'bot_id': 1, 'food_pos': (4, 1)}]
        }
        assert set(p1.current_uni.enemy_food(p1._index)) == {(4, 3), (4, 2), (4, 1)}
        assert set(sim_uni.enemy_food(p1._index)) == {(4, 3), (4, 2)}


class TestSteppingPlayer:
    def test_stepping_players(self):
        test_layout = (
        """ ############
            #0  .  .  1#
            #2        3#
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
            #0  .  .  3#
            #2        1#
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
            #0  .  .  1#
            #2        3#
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
            #0  .  .  1#
            #2        3#
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
            #2            3#
            #              #
            #              #
            #   0      1   #
            #              #
            #              #
            #              #
            #.            .#
            ################ """)
        teams = [
            random_player,
            random_player
        ]
        state = setup_game(teams, layout_dict=parse_layout(test_layout), max_rounds=20, seed=20)
        assert state['bots'][0] == (4, 4)
        assert state['bots'][1] == (4 + 7, 4)

        state = run_game(teams, layout_dict=parse_layout(test_layout), max_rounds=20, seed=20)
        pos_left_bot = state['bots'][0]
        pos_right_bot = state['bots'][1]

        # running again to test seed:
        state = run_game(teams, layout_dict=parse_layout(test_layout), max_rounds=20, seed=20)
        assert state['bots'][0] == pos_left_bot
        assert state['bots'][1] == pos_right_bot

        # running again with other seed:
        state = run_game(teams, layout_dict=parse_layout(test_layout), max_rounds=20, seed=200)
        # most probably, either the left bot or the right bot or both are at
        # a different position
        assert not (state['bots'][0] == pos_left_bot and state['bots'][1] == pos_right_bot)

    def test_random_seeds(self):
        test_layout = (
        """ ################
            #              #
            #              #
            #              #
            #   0      1   #
            #   2      3   #
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
        state = setup_game(team0, layout_dict=parse_layout(test_layout), max_rounds=5, seed=20)
        # play two steps
        play_turn(play_turn(state))
        assert len(player_rngs0) == 2
        # generate some random numbers for each player
        random_numbers0 = [rng.randint(0, 10000) for rng in player_rngs0]
        # teams should have generated a different number
        assert random_numbers0[0] != random_numbers0[1]

        team1, player_rngs1 = init_rng_players()
        state = setup_game(team1, layout_dict=parse_layout(test_layout), max_rounds=5, seed=20)
        # play two steps
        play_turn(play_turn(state))
        assert len(player_rngs1) == 2
        # generate some random numbers for each player
        random_numbers1 = [rng.randint(0, 10000) for rng in player_rngs1]
        # teams should have generated the same numbers as before
        assert random_numbers0 == random_numbers1

        # now, use a different seed
        team2, player_rngs2 = init_rng_players()
        state = setup_game(team2, layout_dict=parse_layout(test_layout), max_rounds=5, seed=200)
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
        #02#.  .#31#
        ############ """)
    teams = [
        speaking_player,
        random_player
    ]
    state = run_game(teams, layout_dict=parse_layout(test_layout), max_rounds=1)
    assert state["say"][0].startswith("Going")
    assert state["say"][1] == ""

