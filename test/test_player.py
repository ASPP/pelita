import pytest
import unittest

from pelita.datamodel import CTFUniverse, east, stop, west
from pelita.game_master import GameMaster
from pelita.player import *
from pelita.players import NQRandomPlayer, RandomPlayer


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
        player_1 = TestPlayer('^<')
        player_2 = StoppingPlayer()
        player_3 = StoppingPlayer()
        teams = [
            SimpleTeam(player_0, player_2),
            SimpleTeam(player_1, player_3)
        ]
        game_master = GameMaster(test_layout, teams, 4, 2, noise=False)
        universe = game_master.universe
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
                player_0.legal_moves
        assert {(0, 1): (15, 3), (0, -1): (15, 1), (0, 0): (15, 2),
                          (1, 0): (16, 2)} == \
                player_1.legal_moves
        assert {(0, 1): (1, 3), (0, -1): (1, 1), (0, 0): (1, 2)} == \
                player_2.legal_moves
        assert {(0, -1): (15, 2), (0, 0): (15, 3)} == \
                player_3.legal_moves

        assert player_1.current_state["round_index"] == None
        assert player_1.current_state["bot_id"] == None

        game_master.play_round()

        assert player_1.current_pos == (15, 2)
        assert player_1.previous_pos == (15, 2)
        assert player_1.initial_pos == (15, 2)
        assert player_1.current_state["round_index"] == 0
        assert player_1.current_state["bot_id"] is None
        assert universe.bots[1].current_pos == (15, 1)
        assert universe.bots[1].initial_pos == (15, 2)
        self.assertUniversesEqual(player_1.current_uni, player_1.universe_states[-1])

        game_master.play_round()

        assert player_1.current_pos == (15, 1)
        assert player_1.previous_pos == (15, 2)
        assert player_1.initial_pos == (15, 2)
        assert player_1.current_state["round_index"] == 1
        assert player_1.current_state["bot_id"] is None
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


class TestTestPlayer:
    def test_test_players(self):
        test_layout = (
        """ ############
            #0  .  .  1#
            #2        3#
            ############ """)
        movements_0 = [east, east]
        movements_1 = [west, west]
        teams = [
            SimpleTeam(TestPlayer(movements_0), TestPlayer(movements_0)),
            SimpleTeam(TestPlayer(movements_1), TestPlayer(movements_1))
        ]
        gm = GameMaster(test_layout, teams, 4, 2)

        assert gm.universe.bots[0].current_pos == (1, 1)
        assert gm.universe.bots[1].current_pos == (10, 1)
        assert gm.universe.bots[2].current_pos == (1, 2)
        assert gm.universe.bots[3].current_pos == (10, 2)

        gm.play()
        assert gm.universe.bots[0].current_pos == (3, 1)
        assert gm.universe.bots[1].current_pos == (8, 1)
        assert gm.universe.bots[2].current_pos == (3, 2)
        assert gm.universe.bots[3].current_pos == (8, 2)

    def test_shorthand(self):
        test_layout = (
        """ ############
            #0  .  .   #
            #         1#
            ############ """)
        num_rounds = 5
        teams = [
            SimpleTeam(TestPlayer('>v<^-)')),
            SimpleTeam(TestPlayer('<^>v-)'))
        ]
        gm = GameMaster(test_layout, teams, 2, num_rounds)
        player0_expected_positions = [(1,1), (2,1), (2,2), (1,2), (1,1)]
        player1_expected_positions = [(10,2), (9,2), (9,1), (10,1), (10,2)]
        gm.set_initial()
        for i in range(num_rounds):
            assert gm.universe.bots[0].current_pos == \
                player0_expected_positions[i]
            assert gm.universe.bots[1].current_pos == \
                player1_expected_positions[i]
            gm.play_round()

    def test_too_many_moves(self):
        test_layout = (
        """ ############
            #0  .  .  1#
            #2        3#
            ############ """)
        movements_0 = [east, east]
        movements_1 = [west, west]
        teams = [
            SimpleTeam(TestPlayer(movements_0), TestPlayer(movements_0)),
            SimpleTeam(TestPlayer(movements_1), TestPlayer(movements_1))
        ]
        gm = GameMaster(test_layout, teams, 4, 3)

        with pytest.raises(ValueError):
            gm.play()

class TestRoundBasedPlayer:
    def test_round_based_players(self):
        test_layout = (
        """ ############
            #0  .  .  1#
            #2        3#
            ############ """)
        movements_0 = [east, east]
        movements_1_0 = {0: west, 2: west}
        movements_1_1 = {2: west}
        teams = [
            SimpleTeam(RoundBasedPlayer(movements_0), RoundBasedPlayer(movements_0)),
            SimpleTeam(RoundBasedPlayer(movements_1_0), RoundBasedPlayer(movements_1_1))
        ]
        gm = GameMaster(test_layout, teams, 4, 3)

        assert gm.universe.bots[0].current_pos == (1, 1)
        assert gm.universe.bots[1].current_pos == (10, 1)
        assert gm.universe.bots[2].current_pos == (1, 2)
        assert gm.universe.bots[3].current_pos == (10, 2)

        gm.play()
        assert gm.universe.bots[0].current_pos == (3, 1)
        assert gm.universe.bots[1].current_pos == (8, 1)
        assert gm.universe.bots[2].current_pos == (3, 2)
        assert gm.universe.bots[3].current_pos == (9, 2)

class TestRandomPlayerSeeds:
    def test_demo_players(self):
        test_layout = (
        """ ################
            #              #
            #              #
            #              #
            #   0      1   #
            #              #
            #              #
            #              #
            #.            .#
            ################ """)
        teams = [
            SimpleTeam(RandomPlayer()),
            SimpleTeam(RandomPlayer())
        ]
        gm = GameMaster(test_layout, teams, 2, 5, seed=20)
        assert gm.universe.bots[0].current_pos == (4, 4)
        assert gm.universe.bots[1].current_pos == (4 + 7, 4)
        gm.play()

        pos_left_bot = gm.universe.bots[0].current_pos
        pos_right_bot = gm.universe.bots[1].current_pos

        # running again to test seed:
        teams = [
            SimpleTeam(RandomPlayer()),
            SimpleTeam(RandomPlayer())
        ]
        gm = GameMaster(test_layout, teams, 2, 5, seed=20)
        gm.play()
        assert gm.universe.bots[0].current_pos == pos_left_bot
        assert gm.universe.bots[1].current_pos == pos_right_bot

        # running again with other seed:
        teams = [
            SimpleTeam(RandomPlayer()),
            SimpleTeam(RandomPlayer())
        ]
        gm = GameMaster(test_layout, teams, 2, 5, seed=200)
        gm.play()
        # most probably, either the left bot or the right bot or both are at
        # a different position
        assert gm.universe.bots[0].current_pos != pos_left_bot \
                     or gm.universe.bots[1].current_pos != pos_right_bot

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
        players_a = [RandomPlayer() for _ in range(4)]

        team_1 = [
            SimpleTeam(players_a[0], players_a[2]),
            SimpleTeam(players_a[1], players_a[3])
        ]
        gm1 = GameMaster(test_layout, team_1, 4, 5, seed=20)
        gm1.set_initial()
        random_numbers_a = [player.rnd.randint(0, 10000) for player in players_a]
        # check that each player has a different seed (if randomness allows)
        assert len(set(random_numbers_a)) == 4, "Probably not all player seeds were unique."

        players_b = [RandomPlayer() for _ in range(4)]

        team_2 = [
            SimpleTeam(players_b[0], players_b[2]),
            SimpleTeam(players_b[1], players_b[3])
        ]
        gm2 = GameMaster(test_layout, team_2, 4, 5, seed=20)
        gm2.set_initial()
        random_numbers_b = [player.rnd.randint(0, 10000) for player in players_b]
        assert random_numbers_a == random_numbers_b

        players_c = [RandomPlayer() for _ in range(4)]

        team_3 = [
            SimpleTeam(players_c[0], players_c[2]),
            SimpleTeam(players_c[1], players_c[3])
        ]
        gm3 = GameMaster(test_layout, team_3, 4, 5, seed=200)
        gm3.set_initial()
        random_numbers_c = [player.rnd.randint(0, 10000) for player in players_c]

        assert random_numbers_a != random_numbers_c


class TestNQRandom_Player:
    def test_demo_players(self):
        test_layout = (
        """ ############
            #0#.   .# 1#
            ############ """)
        team = [
            SimpleTeam(NQRandomPlayer()),
            SimpleTeam(NQRandomPlayer())
        ]
        gm = GameMaster(test_layout, team, 2, 1)
        gm.play()
        assert gm.universe.bots[0].current_pos == (1, 1)
        assert gm.universe.bots[1].current_pos == (9, 1)

    def test_path(self):
        test_layout = (
        """ ############
            #  . # .# ##
            # ## #  # ##
            #0#.   .##1#
            ############ """)
        team = [
            SimpleTeam(NQRandomPlayer()),
            SimpleTeam(NQRandomPlayer())
        ]
        gm = GameMaster(test_layout, team, 2, 7)
        gm.play()
        assert gm.universe.bots[0].current_pos == (4, 3)
        assert gm.universe.bots[1].current_pos == (10, 3)


class TestSpeakingPlayer:
    def test_demo_players(self):
        test_layout = (
        """ ############
            #0 #.  .# 1#
            ############ """)
        team = [
            SimpleTeam(SpeakingPlayer()),
            SimpleTeam(RandomPlayer())
        ]
        gm = GameMaster(test_layout, team, 2, 1)
        gm.play()
        assert gm.game_state["bot_talk"][0].startswith("Going")
        assert gm.game_state["bot_talk"][1] == ""


class TestSimpleTeam:

    class BrokenPlayer_with_nothing:
        pass

    class BrokenPlayer_without_set_initial:
        def _set_initial(self, universe):
            pass

    class BrokenPlayer_without_get_move:
        def _set_initial(self, universe):
            pass

    def test_player_api_methods(self):
        with pytest.raises(TypeError):
            SimpleTeam(self.BrokenPlayer_with_nothing())
        with pytest.raises(TypeError):
            SimpleTeam(self.BrokenPlayer_without_set_initial())
        with pytest.raises(TypeError):
            SimpleTeam(self.BrokenPlayer_without_get_move())

    def test_init(self):
        with pytest.raises(ValueError):
            SimpleTeam()
        object_which_is_neither_string_nor_team = 5
        with pytest.raises(TypeError):
            SimpleTeam(object_which_is_neither_string_nor_team)

        team0 = SimpleTeam("my team")
        assert team0.team_name == "my team"
        assert len(team0._players) == 0

        team1 = SimpleTeam("my team", TestPlayer([]))
        assert team1.team_name == "my team"
        assert len(team1._players) == 1

        team2 = SimpleTeam("my other team", TestPlayer([]), TestPlayer([]))
        assert team2.team_name == "my other team"
        assert len(team2._players) == 2

        team3 = SimpleTeam(TestPlayer([]))
        assert team3.team_name == ""
        assert len(team3._players) == 1

        team4 = SimpleTeam(TestPlayer([]), TestPlayer([]))
        assert team4.team_name == ""
        assert len(team4._players) == 2

    def test_too_few_players(self):
        layout = (
            """ ######
                #0123#
                ###### """
        )
        dummy_universe = CTFUniverse.create(layout, 4)
        team1 = SimpleTeam(TestPlayer('^'))

        with pytest.raises(ValueError):
            team1.set_initial(0, dummy_universe, {})

class TestAbstracts:
    class BrokenPlayer(AbstractPlayer):
        pass

    def test_AbstractPlayer(self):
        with pytest.raises(TypeError):
            AbstractPlayer()

    def test_BrokenPlayer(self):
        with pytest.raises(TypeError):
            self.BrokenPlayer()
