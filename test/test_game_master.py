# -*- coding: utf-8 -*-

import unittest
import time
import collections
import pelita
from pelita.datamodel import Wall, Free, Food, create_CTFUniverse, KILLPOINTS

from pelita.game_master import GameMaster, UniverseNoiser, AStarNoiser, ManhattanNoiser, PlayerTimeout
from pelita.player import AbstractPlayer, SimpleTeam, TestPlayer, StoppingPlayer
from pelita.viewer import AbstractViewer, DevNullViewer
from pelita.graph import AdjacencyList


class TestGameMaster(unittest.TestCase):
    test_layout = """ ####
                      #01#
                      #### """
    game_master = GameMaster(test_layout, 2, 200)

    class BrokenViewer_without_observe(object):
        pass

    def test_viewer_api_methods(self):
        viewer = self.BrokenViewer_without_observe()
        self.game_master.register_viewer(viewer)

    def test_team_names(self):
        test_layout = (
        """ ##################
            #0#.  .  # .     #
            #2#####    #####1#
            #     . #  .  .#3#
            ################## """)

        game_master = GameMaster(test_layout, 4, 200)

        team_1 = SimpleTeam(TestPlayer([]), TestPlayer([]))
        team_2 = SimpleTeam(TestPlayer([]), TestPlayer([]))

        game_master.register_team(team_1, team_name="team1")
        game_master.register_team(team_2, team_name="team2")

        game_master.set_initial()
        self.assertEqual(game_master.universe.teams[0].name, "team1")
        self.assertEqual(game_master.universe.teams[1].name, "team2")

        # check that all players know it, before the game started
        self.assertEqual(team_1._players[0].current_uni.teams[0].name, "team1")
        self.assertEqual(team_1._players[0].current_uni.teams[1].name, "team2")
        self.assertEqual(team_1._players[1].current_uni.teams[0].name, "team1")
        self.assertEqual(team_1._players[1].current_uni.teams[1].name, "team2")

        self.assertEqual(team_2._players[0].current_uni.teams[0].name, "team1")
        self.assertEqual(team_2._players[0].current_uni.teams[1].name, "team2")
        self.assertEqual(team_2._players[1].current_uni.teams[0].name, "team1")
        self.assertEqual(team_2._players[1].current_uni.teams[1].name, "team2")

    def test_too_few_registered_teams(self):
        test_layout_4 = (
        """ ##################
            #0#.  .  # .     #
            #2#####    #####1#
            #     . #  .  .#3#
            ################## """)
        game_master = GameMaster(test_layout_4, 4, 200)

        team_1 = SimpleTeam(TestPlayer([]), TestPlayer([]))
        game_master.register_team(team_1)

        self.assertEqual(len(game_master.universe.teams), 2)
        self.assertRaises(IndexError, game_master.play)

    def test_too_many_registered_teams(self):
        test_layout_4 = (
        """ ##################
            #0#.  .  # .     #
            #2#####    #####1#
            #     . #  .  .#3#
            ################## """)
        game_master = GameMaster(test_layout_4, 4, 200)

        team_1 = SimpleTeam(TestPlayer([]), TestPlayer([]))
        team_2 = SimpleTeam(TestPlayer([]), TestPlayer([]))
        team_3 = SimpleTeam(TestPlayer([]), TestPlayer([]))
        game_master.register_team(team_1)
        game_master.register_team(team_2)
        game_master.register_team(team_3)

        self.assertEqual(len(game_master.universe.teams), 2)
        self.assertRaises(IndexError, game_master.play)


class TestUniverseNoiser(unittest.TestCase):
    if not hasattr(unittest.TestCase, 'assertItemsEqual'):
        def assertItemsEqual(self, a, b, disp):
            self.assertEqual(sorted(a), sorted(b), disp)

    def test_uniform_noise_a_star(self):
        test_layout = (
        """ ##################
            # #.  .  # .     #
            # #####    ##### #
            #  0  . #  .  .#1#
            ################## """)
        universe = create_CTFUniverse(test_layout, 2)
        noiser = AStarNoiser(universe.copy())

        position_bucket = collections.defaultdict(int)
        for i in range(100):
            new = noiser.uniform_noise(universe.copy(), 1)
            self.assertTrue(new.bots[0].noisy)
            position_bucket[new.bots[0].current_pos] += 1
        self.assertEqual(100, sum(position_bucket.itervalues()))
        # Since this is a randomized algorithm we need to be a bit lenient with
        # our tests. We check that each position was selected at least once.
        expected = [(1, 2), (7, 3), (1, 3), (3, 3), (6, 3),
                    (2, 3), (4, 3), (1, 1), (5, 3)]
        self.assertItemsEqual(position_bucket, expected, position_bucket)

    def test_uniform_noise_manhattan(self):
        test_layout = (
        """ ##################
            # #.  .  # .     #
            # #####    ##### #
            #  0  . #  .  .#1#
            ################## """)
        universe = create_CTFUniverse(test_layout, 2)
        noiser = ManhattanNoiser(universe.copy())

        position_bucket = collections.defaultdict(int)
        for i in range(200):
            new = noiser.uniform_noise(universe.copy(), 1)
            self.assertTrue(new.bots[0].noisy)
            position_bucket[new.bots[0].current_pos] += 1
        self.assertEqual(200, sum(position_bucket.itervalues()))
        # Since this is a randomized algorithm we need to be a bit lenient with
        # our tests. We check that each position was selected at least once.
        expected = [ (1, 1), (1, 2), (1, 3), (2, 3), (3, 3),
                     (4, 3), (5, 3), (6, 3), (7, 3), (7, 2),
                     (6, 1), (5, 1), (4, 1), (3, 1) ]
        self.assertItemsEqual(position_bucket, expected, position_bucket)
    

    def test_uniform_noise_4_bots_a_star(self):
        test_layout = (
        """ ##################
            # #. 2.  # .     #
            # #####    #####3#
            #  0  . #  .  .#1#
            ################## """)
        universe = create_CTFUniverse(test_layout, 4)
        noiser = AStarNoiser(universe.copy())

        expected_0 = [(1, 2), (7, 3), (1, 3), (3, 3), (6, 3),
                      (2, 3), (4, 3), (1, 1), (5, 3)]
        position_bucket_0 = collections.defaultdict(int)

        expected_2 = [(7, 3), (8, 2), (7, 1), (8, 1), (6, 1), (3, 1), (5, 1),
                      (4, 1), (7, 2)]
        position_bucket_2 = collections.defaultdict(int)

        for i in range(100):
            new = noiser.uniform_noise(universe.copy(), 1)
            self.assertTrue(new.bots[0].noisy)
            self.assertTrue(new.bots[2].noisy)
            position_bucket_0[new.bots[0].current_pos] += 1
            position_bucket_2[new.bots[2].current_pos] += 1
        self.assertEqual(100, sum(position_bucket_0.itervalues()))
        self.assertEqual(100, sum(position_bucket_2.itervalues()))
        # Since this is a randomized algorithm we need to be a bit lenient with
        # our tests. We check that each position was selected at least once.
        self.assertItemsEqual(position_bucket_0, expected_0, sorted(position_bucket_0.keys()))
        self.assertItemsEqual(position_bucket_2, expected_2, sorted(position_bucket_2.keys()))

    def test_uniform_noise_4_bots_manhattan(self):
        test_layout = (
        """ ##################
            # #. 2.  # .     #
            # #####    #####3#
            #   0  . # .  .#1#
            ################## """)
        universe = create_CTFUniverse(test_layout, 4)
        noiser = ManhattanNoiser(universe.copy())

        expected_0 = [ (1, 1), (1, 2), (1, 3), (2, 3), (3, 3),
                       (4, 3), (5, 3), (6, 3), (7, 3), (7, 2),
                       (7, 1), (6, 1), (5, 1), (4, 1), (3, 1),
                       (8, 2), (8, 3)]

        position_bucket_0 = collections.defaultdict(int)

        expected_2 = [ (1, 1), (1, 2), (2, 3), (3, 3), (4, 3),
                       (5, 3), (6, 3), (7, 3), (8, 2), (8, 1),
                       (7, 1), (6, 1), (5, 1), (4, 1), (3, 1),
                       (9, 2), (8, 3), (7, 2)]
        position_bucket_2 = collections.defaultdict(int)

        for i in range(200):
            new = noiser.uniform_noise(universe.copy(), 1)
            self.assertTrue(new.bots[0].noisy)
            self.assertTrue(new.bots[2].noisy)
            position_bucket_0[new.bots[0].current_pos] += 1
            position_bucket_2[new.bots[2].current_pos] += 1
        self.assertEqual(200, sum(position_bucket_0.itervalues()))
        self.assertEqual(200, sum(position_bucket_2.itervalues()))
        # Since this is a randomized algorithm we need to be a bit lenient with
        # our tests. We check that each position was selected at least once.
        self.assertItemsEqual(position_bucket_0, expected_0, sorted(position_bucket_0.keys()))
        self.assertItemsEqual(position_bucket_2, expected_2, sorted(position_bucket_2.keys()))

    def test_uniform_noise_4_bots_no_noise_a_star(self):
        test_layout = (
        """ ##################
            # #.  .  # . 2   #
            # #####    #####3#
            #  0  . #  .  .#1#
            ################## """)
        universe = create_CTFUniverse(test_layout, 4)
        noiser = AStarNoiser(universe.copy())

        expected_0 = [(1, 2), (7, 3), (1, 3), (3, 3), (6, 3),
                      (2, 3), (4, 3), (1, 1), (5, 3)]
        position_bucket_0 = collections.defaultdict(int)

        bot_2_pos = (13, 1)
        position_bucket_2 = {bot_2_pos : 0}

        for i in range(100):
            new = noiser.uniform_noise(universe.copy(), 1)
            self.assertTrue(new.bots[0].noisy)
            self.assertFalse(new.bots[2].noisy)
            position_bucket_0[new.bots[0].current_pos] += 1
            position_bucket_2[new.bots[2].current_pos] += 1
        self.assertEqual(100, sum(position_bucket_0.itervalues()))
        self.assertEqual(100, sum(position_bucket_2.itervalues()))
        # Since this is a randomized algorithm we need to be a bit lenient with
        # our tests. We check that each position was selected at least once.
        self.assertItemsEqual(position_bucket_0, expected_0, position_bucket_0)

        # bots should never have been noised
        self.assertEqual(100, position_bucket_2[bot_2_pos])

    def test_uniform_noise_4_bots_no_noise_manhattan(self):
        test_layout = (
        """ ##################
            # #.  .  # . 2   #
            # #####    #####3#
            #  0  . #  .  .#1#
            ################## """)
        universe = create_CTFUniverse(test_layout, 4)
        noiser = ManhattanNoiser(universe.copy())

        expected_0 = [ (1, 1), (3, 1), (4, 1), (5, 1), (6, 1),
                       (1, 2), (1, 3), (2, 3), (3, 3), (4, 3), (5, 3),
                       (6, 3), (7, 3), (7, 2) ]
        position_bucket_0 = collections.defaultdict(int)

        bot_2_pos = (13, 1)
        position_bucket_2 = {bot_2_pos : 0}

        for i in range(200):
            new = noiser.uniform_noise(universe.copy(), 1)
            self.assertTrue(new.bots[0].noisy)
            self.assertFalse(new.bots[2].noisy)
            position_bucket_0[new.bots[0].current_pos] += 1
            position_bucket_2[new.bots[2].current_pos] += 1
        self.assertEqual(200, sum(position_bucket_0.itervalues()))
        self.assertEqual(200, sum(position_bucket_2.itervalues()))
        # Since this is a randomized algorithm we need to be a bit lenient with
        # our tests. We check that each position was selected at least once.
        self.assertItemsEqual(position_bucket_0, expected_0, position_bucket_0)

        # bots should never have been noised
        self.assertEqual(200, position_bucket_2[bot_2_pos])

    def test_noise_a_star_failure(self):
        test_layout = (
        """ ##################
            # #.  .  # . 2   #
            # #####    #####3#
            #  0# . #  .  . 1#
            ################## """)
        # noiser should not find a connection
        universe = create_CTFUniverse(test_layout, 4)

        positions = [b.current_pos for b in universe.bots]

        noiser = AStarNoiser(universe.copy())
        new_uni = noiser.uniform_noise(universe.copy(), 0)
        new_positions = [b.current_pos for b in new_uni.bots]

        # assume not all bots (except 0 and 2) are in the original position anymore
        self.assertEqual(positions[0::2], new_positions[0::2])
        self.assertNotEqual(positions[1::2], new_positions[1::2],
                            "Testing randomized function, may fail sometimes.")

    def test_noise_manhattan_failure(self):
        test_layout = (
        """ ##################
            ########## . 2   #
            ########## #####3#
            ###0###### .  . 1#
            ################## """)
        # noiser should not find a connection
        universe = create_CTFUniverse(test_layout, 4)

        positions = [b.current_pos for b in universe.bots]

        noiser = ManhattanNoiser(universe.copy())
        new_uni = noiser.uniform_noise(universe.copy(), 0)
        new_positions = [b.current_pos for b in new_uni.bots]

        # assume not all bots (except 0 and 2) are in the original position anymore
        self.assertEqual(positions[0::2], new_positions[0::2])
        self.assertNotEqual(positions[1::2], new_positions[1::2],
                            "Testing randomized function, may fail sometimes.")

class TestAbstracts(unittest.TestCase):
    class BrokenViewer(AbstractViewer):
        pass

    def test_AbstractViewer(self):
        self.assertRaises(TypeError, AbstractViewer)

    def test_BrokenViewer(self):
        self.assertRaises(TypeError, self.BrokenViewer)

class TestGame(unittest.TestCase):

    def test_game(self):

        test_start = (
            """ ######
                #0 . #
                #.. 1#
                ###### """)

        number_bots = 2

        # The problem here is that the layout does not allow us to specify a
        # different inital position and current position. When testing universe
        # equality by comparing its string representation, this does not matter.
        # But if we want to compare using the __eq__ method, but specify the
        # target as ascii encoded maze/layout we need to convert the layout to a
        # CTFUniverse and then modify the initial positions. For this we define
        # a closure here to quickly generate a target universe to compare to.
        # Also we adapt the score, in case food has been eaten

        def create_TestUniverse(layout, black_score=0, white_score=0):
            initial_pos = [(1, 1), (4, 2)]
            universe = create_CTFUniverse(layout, number_bots)
            universe.teams[0].score = black_score
            universe.teams[1].score = white_score
            for i, pos in enumerate(initial_pos):
                universe.bots[i].initial_pos = pos
            if not Food in universe.maze[1, 2]:
                universe.teams[1]._score_point()
            if not Food in universe.maze[2, 2]:
                universe.teams[1]._score_point()
            if not Food in universe.maze[3, 1]:
                universe.teams[0]._score_point()
            return universe


        gm = GameMaster(test_start, number_bots, 200)
        gm.register_team(SimpleTeam(TestPlayer('>-v>>>')))
        gm.register_team(SimpleTeam(TestPlayer('<<-<<<')))

        gm.register_viewer(DevNullViewer())

        gm.set_initial()
        gm.play_round()
        test_first_round = (
            """ ######
                # 0. #
                #..1 #
                ###### """)
        self.assertEqual(create_TestUniverse(test_first_round), gm.universe)

        gm.play_round()
        test_second_round = (
            """ ######
                # 0. #
                #.1  #
                ###### """)
        self.assertEqual(create_TestUniverse(test_second_round), gm.universe)

        gm.play_round()
        test_third_round = (
            """ ######
                #  . #
                #.0 1#
                ###### """)
        self.assertEqual(create_TestUniverse(test_third_round,
            black_score=KILLPOINTS), gm.universe)

        gm.play_round()
        test_fourth_round = (
            """ ######
                #0 . #
                #. 1 #
                ###### """)
        self.assertEqual(create_TestUniverse(test_fourth_round,
            black_score=KILLPOINTS, white_score=KILLPOINTS), gm.universe)

        gm.play_round()
        test_fifth_round = (
            """ ######
                # 0. #
                #.1  #
                ###### """)
        self.assertEqual(create_TestUniverse(test_fifth_round,
            black_score=KILLPOINTS, white_score=KILLPOINTS), gm.universe)

        print gm.universe.pretty
        gm.play_round()
        test_sixth_round = (
            """ ######
                #  0 #
                #1   #
                ###### """)
        print gm.universe.pretty
        self.assertEqual(create_TestUniverse(test_sixth_round,
            black_score=KILLPOINTS, white_score=KILLPOINTS), gm.universe)

        # now play the full game
        gm = GameMaster(test_start, number_bots, 200)
        gm.register_team(SimpleTeam(TestPlayer('>-v>>>')))
        gm.register_team(SimpleTeam(TestPlayer('<<-<<<')))
        gm.play()
        test_sixth_round = (
            """ ######
                #  0 #
                #1   #
                ###### """)
        self.assertEqual(create_TestUniverse(test_sixth_round,
            black_score=KILLPOINTS, white_score=KILLPOINTS), gm.universe)

    def test_malicous_player(self):
        free_obj = Free

        class MaliciousPlayer(AbstractPlayer):
            def _get_move(self, universe, game_state):
                universe.teams[0].score = 100
                universe.bots[0].current_pos = (2,2)
                universe.maze[0,0] = free_obj
                return {"move": (0,0)}

            def get_move(self):
                pass

        test_layout = (
            """ ######
                #0 . #
                #.. 1#
                ###### """)
        gm = GameMaster(test_layout, 2, 200)

        original_universe = gm.universe.copy()

        test_self = self
        class TestMaliciousPlayer(AbstractPlayer):
            def get_move(self):
                print id(original_universe.maze)
                print id(gm.universe.maze)
                # universe should have been altered because the
                # Player is really malicious
                test_self.assertNotEqual(original_universe, gm.universe)
                return (0,0)

        gm.register_team(SimpleTeam(MaliciousPlayer()))
        gm.register_team(SimpleTeam(TestMaliciousPlayer()))

        gm.set_initial()
        gm.play_round()

        test_self.assertNotEqual(original_universe, gm.universe)

    def test_failing_player(self):
        class FailingPlayer(AbstractPlayer):
            def get_move(self):
                return 1

        test_layout = (
            """ ######
                #0 . #
                #.. 1#
                ###### """)
        gm = GameMaster(test_layout, 2, 1)

        gm.register_team(SimpleTeam(FailingPlayer()))
        gm.register_team(SimpleTeam(TestPlayer("^")))

        gm.play()
        self.assertEqual(gm.game_state["timeout_teams"], [1, 0])

    def test_viewer_may_change_gm(self):
        free_obj = Free

        class MeanViewer(AbstractViewer):
            def set_initial(self, universe):
                universe.teams[1].score = 50

            def observe(self, universe, game_state):
                universe.teams[0].score = 100
                universe.bots[0].current_pos = (4,2)
                universe.maze[0,0] = free_obj

                game_state["team_wins"] = 0

        test_start = (
            """ ######
                #0 . #
                #.. 1#
                ###### """)

        number_bots = 2

        gm = GameMaster(test_start, number_bots, 200)
        gm.register_team(SimpleTeam(TestPlayer([(0,0)])))
        gm.register_team(SimpleTeam(TestPlayer([(0,0)])))

        original_universe = gm.universe.copy()

        test_self = self
        class TestViewer(AbstractViewer):
            def observe(self, universe, game_state):
                # universe has been altered
                test_self.assertNotEqual(original_universe, gm.universe)

        gm.register_viewer(MeanViewer())
        gm.register_viewer(TestViewer())

        gm.set_initial()
        gm.play_round()

        self.assertNotEqual(original_universe, gm.universe)

    def test_win_on_timeout_team_0(self):
        test_start = (
            """ ######
                #0 ..#
                #.. 1#
                ###### """)
        # the game lasts two rounds, enough time for bot 1 to eat food
        NUM_ROUNDS = 2
        gm = GameMaster(test_start, 2, game_time=NUM_ROUNDS)
        # bot 1 moves east twice to eat the single food
        gm.register_team(SimpleTeam(TestPlayer('>>')))
        gm.register_team(SimpleTeam(StoppingPlayer()))

        # this test viewer caches all events lists seen through observe
        class TestViewer(AbstractViewer):
            def __init__(self):
                self.cache = list()
            def observe(self, universe, game_state):
                self.cache.append(game_state)

        # run the game
        tv = TestViewer()
        gm.register_viewer(tv)
        gm.set_initial()
        gm.play()

        # check
        self.assertTrue(tv.cache[-1]["team_wins"] is not None)
        self.assertEqual(tv.cache[-1]["team_wins"], 0)
        self.assertEqual(gm.game_state["round_index"], NUM_ROUNDS)

    def test_win_on_timeout_team_1(self):
        test_start = (
            """ ######
                #0 ..#
                #.. 1#
                ###### """)
        # the game lasts two rounds, enough time for bot 1 to eat food
        NUM_ROUNDS = 2
        gm = GameMaster(test_start, 2, game_time=NUM_ROUNDS)
        gm.register_team(SimpleTeam(StoppingPlayer()))
        # bot 1 moves west twice to eat the single food
        gm.register_team(SimpleTeam(TestPlayer('<<')))

        # this test viewer caches all events lists seen through observe
        class TestViewer(AbstractViewer):
            def __init__(self):
                self.cache = list()
            def observe(self, universe, game_state):
                self.cache.append(game_state)

        # run the game
        tv = TestViewer()
        gm.register_viewer(tv)
        gm.set_initial()
        gm.play()

        # check
        self.assertTrue(tv.cache[-1]["team_wins"] is not None)
        self.assertEqual(tv.cache[-1]["team_wins"], 1)
        self.assertEqual(gm.game_state["round_index"], NUM_ROUNDS)

    def test_draw_on_timeout(self):
        test_start = (
            """ ######
                #0 . #
                # . 1#
                ###### """)
        # the game lasts one round, and then draws
        NUM_ROUNDS = 1
        gm = GameMaster(test_start, 2, game_time=NUM_ROUNDS)
        # players do nothing
        gm.register_team(SimpleTeam(StoppingPlayer()))
        gm.register_team(SimpleTeam(StoppingPlayer()))

        # this test viewer caches all events lists seen through observe
        class TestViewer(AbstractViewer):
            def __init__(self):
                self.cache = list()
            def observe(self, universe, game_state):
                self.cache.append(game_state)

        # run the game
        tv = TestViewer()
        gm.register_viewer(tv)
        gm.set_initial()
        gm.play()

        # check
        self.assertTrue(tv.cache[-1]["game_draw"])
        self.assertEqual(gm.game_state["round_index"], NUM_ROUNDS)

    def test_win_on_eating_all(self):
        test_start = (
            """ ######
                #0 . #
                # . 1#
                ###### """
        )
        # bot 1 eats all the food and the game stops
        gm = GameMaster(test_start, 2, 100)
        # players do nothing
        gm.register_team(SimpleTeam(StoppingPlayer()))
        gm.register_team(SimpleTeam(TestPlayer('<<<')))

        # this test viewer caches all events lists seen through observe
        class TestViewer(AbstractViewer):
            def __init__(self):
                self.cache = list()
            def observe(self, universe, game_state):
                self.cache.append(game_state)

        # run the game
        tv = TestViewer()
        gm.register_viewer(tv)
        gm.set_initial()
        gm.play()

        # check
        self.assertTrue(tv.cache[-1]["team_wins"] is not None)
        self.assertEqual(tv.cache[-1]["team_wins"], 1)
        self.assertEqual(tv.cache[-1]["round_index"], 1)
        self.assertEqual(gm.game_state["round_index"], 1)

    def test_lose_on_eating_all(self):
        test_start = (
            """ ######
                #0 . #
                # . 1#
                ###### """
        )
        # bot 1 eats all the food and the game stops
        gm = GameMaster(test_start, 2, 100)
        # players do nothing
        gm.register_team(SimpleTeam(StoppingPlayer()))
        gm.register_team(SimpleTeam(TestPlayer('<<<')))
        gm.universe.teams[0].score = 2

        # this test viewer caches all events lists seen through observe
        class TestViewer(AbstractViewer):
            def __init__(self):
                self.cache = list()
            def observe(self, universe, game_state):
                self.cache.append(game_state)

        # run the game
        tv = TestViewer()
        gm.register_viewer(tv)
        gm.set_initial()
        gm.play()

        # check
        self.assertEqual(tv.cache[-1]["round_index"], 1)
        self.assertEqual(gm.universe.teams[0].score, 2)
        self.assertEqual(gm.universe.teams[1].score, 1)
        self.assertTrue(tv.cache[-1]["team_wins"] is not None)
        self.assertEqual(tv.cache[-1]["team_wins"], 0)
        self.assertEqual(gm.game_state["round_index"], 1)

    def test_lose_5_timeouts(self):
        # 0 must move back and forth because of random steps
        test_start = (
            """ ######
                #0 #.#
                ###  #
                ##. 1#
                ###### """
        )
        # the game lasts one round, and then draws
        gm = GameMaster(test_start, 2, 100, max_timeouts=5)
        # players do nothing
        class TimeOutPlayer(AbstractPlayer):
            def get_move(self):
                raise PlayerTimeout

        gm.register_team(SimpleTeam(TimeOutPlayer()))
        gm.register_team(SimpleTeam(StoppingPlayer()))

        # this test viewer caches all events lists seen through observe
        class TestViewer(AbstractViewer):
            def __init__(self):
                self.cache = list()
            def observe(self, universe, game_state):
                self.cache.append(game_state)

        # run the game
        tv = TestViewer()
        gm.register_viewer(tv)
        gm.set_initial()

        self.assertEqual(gm.universe.bots[0].current_pos, (1,1))

        gm.play()

        # check
        self.assertEqual(gm.game_state["max_timeouts"], 5)
        self.assertEqual(tv.cache[-1]["round_index"], gm.game_state["max_timeouts"] - 1)
        self.assertEqual(gm.universe.teams[0].score, 0)
        self.assertEqual(gm.universe.teams[1].score, 0)
        self.assertEqual(gm.universe.bots[0].current_pos, (2,1))
        self.assertTrue(tv.cache[-1]["team_wins"] is not None)
        self.assertEqual(tv.cache[-1]["team_wins"], 1)

    def test_play_step(self):

        test_start = (
            """ ########
                # 0  ..#
                #..  1 #
                ######## """)

        number_bots = 2

        gm = GameMaster(test_start, number_bots, 4)
        gm.register_team(SimpleTeam(TestPlayer('>>>>')))
        gm.register_team(SimpleTeam(TestPlayer('<<<<')))

        gm.set_initial()

        gm.play_round()
        self.assertEqual(gm.universe.bots[0].current_pos, (3,1))
        self.assertEqual(gm.universe.bots[1].current_pos, (4,2))
        self.assertEqual(gm.game_state["round_index"], 0)
        self.assertEqual(gm.game_state["bot_id"], 1)
        self.assertEqual(gm.game_state["finished"], False)

        gm.play_step()
        self.assertEqual(gm.universe.bots[0].current_pos, (4,1))
        self.assertEqual(gm.universe.bots[1].current_pos, (4,2))
        self.assertEqual(gm.game_state["round_index"], 1)
        self.assertEqual(gm.game_state["bot_id"], 0)
        self.assertEqual(gm.game_state["finished"], False)

        gm.play_step()
        self.assertEqual(gm.universe.bots[0].current_pos, (4,1))
        self.assertEqual(gm.universe.bots[1].current_pos, (3,2))
        self.assertEqual(gm.game_state["round_index"], 1)
        self.assertEqual(gm.game_state["bot_id"], 1)
        self.assertEqual(gm.game_state["finished"], False)

        gm.play_step()
        self.assertEqual(gm.universe.bots[0].current_pos, (5,1))
        self.assertEqual(gm.universe.bots[1].current_pos, (3,2))
        self.assertEqual(gm.game_state["round_index"], 2)
        self.assertEqual(gm.game_state["bot_id"], 0)
        self.assertEqual(gm.game_state["finished"], False)

        gm.play_step()
        self.assertEqual(gm.universe.bots[0].current_pos, (5,1))
        self.assertEqual(gm.universe.bots[1].current_pos, (2,2))
        self.assertEqual(gm.game_state["round_index"], 2)
        self.assertEqual(gm.game_state["bot_id"], 1)
        self.assertEqual(gm.game_state["finished"], False)

        gm.play_round()
        # first call tries to finish current round (which already is finished)
        # so nothing happens
        self.assertEqual(gm.universe.bots[0].current_pos, (5,1))
        self.assertEqual(gm.universe.bots[1].current_pos, (2,2))
        self.assertEqual(gm.game_state["round_index"], 2)
        self.assertEqual(gm.game_state["bot_id"], 1)
        self.assertEqual(gm.game_state["finished"], False)

        gm.play_round()
        # second call works
        self.assertEqual(gm.universe.bots[0].current_pos, (6,1))
        self.assertEqual(gm.universe.bots[1].current_pos, (1,2))
        self.assertEqual(gm.game_state["round_index"], 3)
        self.assertEqual(gm.game_state["bot_id"], 1)
        self.assertEqual(gm.game_state["finished"], True)

        # Game finished because all food was eaten
        # (hence round_index == 2 and bot_id == 1)
        # nothing happens anymore
        gm.play_round()
        self.assertEqual(gm.universe.bots[0].current_pos, (6,1))
        self.assertEqual(gm.universe.bots[1].current_pos, (1,2))
        self.assertEqual(gm.game_state["round_index"], 3)
        self.assertEqual(gm.game_state["bot_id"], 1)
        self.assertEqual(gm.game_state["finished"], True)

        # nothing happens anymore
        gm.play_round()
        self.assertEqual(gm.universe.bots[0].current_pos, (6,1))
        self.assertEqual(gm.universe.bots[1].current_pos, (1,2))
        self.assertEqual(gm.game_state["round_index"], 3)
        self.assertEqual(gm.game_state["bot_id"], 1)
        self.assertEqual(gm.game_state["finished"], True)

    def test_kill_count(self):
        test_start = (
            """ ######
                #0  1#
                #....#
                ###### """)
        # the game lasts two rounds, enough time for bot 1 to eat food
        NUM_ROUNDS = 5
        gm = GameMaster(test_start, 2, game_time=NUM_ROUNDS)
        gm.register_team(SimpleTeam(TestPlayer('>--->')))
        # bot 1 moves west twice to eat the single food
        gm.register_team(SimpleTeam(TestPlayer('<<<<<')))

        gm.set_initial()
        gm.play_round()
        self.assertEqual(gm.game_state["times_killed"], [0, 0])
        gm.play_round()
        self.assertEqual(gm.game_state["times_killed"], [0, 1])
        gm.play_round()
        self.assertEqual(gm.game_state["times_killed"], [0, 1])
        gm.play_round()
        self.assertEqual(gm.game_state["times_killed"], [0, 2])
        gm.play_round()
        self.assertEqual(gm.game_state["times_killed"], [1, 2])