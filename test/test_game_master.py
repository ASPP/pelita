# -*- coding: utf-8 -*-

import unittest
import time
import pelita
from pelita.datamodel import north, south, east, west, stop,\
        Wall, Free, Food, TeamWins, GameDraw, BotMoves, create_CTFUniverse,\
        KILLPOINTS
from pelita.game_master import GameMaster, UniverseNoiser, PlayerTimeout
from pelita.player import AbstractPlayer, SimpleTeam, TestPlayer, StoppingPlayer
from pelita.viewer import AbstractViewer, DevNullViewer
from pelita.graph import AdjacencyList


class TestGameMaster(unittest.TestCase):

    def test_basics(self):
        test_layout = (
        """ ##################
            #0#.  .  # .     #
            #2#####    #####1#
            #     . #  .  .#3#
            ################## """)

        game_master = GameMaster(test_layout, 4, 200)

        class BrokenViewer(AbstractViewer):
            pass

        class BrokenPlayer(AbstractPlayer):
            pass

        self.assertRaises(TypeError, game_master.register_viewer, BrokenViewer())
#        self.assertRaises(TypeError, game_master.register_player, BrokenPlayer())
        self.assertRaises(IndexError, game_master.play)

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


class TestUniverseNoiser(unittest.TestCase):



    def test_uniform_noise(self):
        test_layout = (
        """ ##################
            # #.  .  # .     #
            # #####    ##### #
            #  0  . #  .  .#1#
            ################## """)
        universe = create_CTFUniverse(test_layout, 2)
        noiser = UniverseNoiser(universe.copy())

        position_bucket = dict(((i, 0)
            for i in [(1, 2), (7, 3), (1, 3), (3, 3), (6, 3),
                (2, 3), (4, 3), (1, 1), (5, 3)]))
        for i in range(100):
            new = noiser.uniform_noise(universe.copy(), 1)
            self.assertTrue(new.bots[0].noisy)
            position_bucket[new.bots[0].current_pos] += 1
        self.assertEqual(100, sum(position_bucket.itervalues()))
        # Since this is a randomized algorithm we need to be a bit lenient with
        # our tests. We check that each position was selected at least once and
        # check that it was selected a minimum of five times.
        for v in position_bucket.itervalues():
            self.assertTrue(v != 0)
            self.assertTrue(v >= 5, 'Testing randomized function, may fail sometimes.')

    def test_uniform_noise_4_bots(self):
        test_layout = (
        """ ##################
            # #. 2.  # .     #
            # #####    #####3#
            #  0  . #  .  .#1#
            ################## """)
        universe = create_CTFUniverse(test_layout, 4)
        noiser = UniverseNoiser(universe.copy())

        position_bucket_0 = dict(((i, 0)
            for i in [(1, 2), (7, 3), (1, 3), (3, 3), (6, 3),
                (2, 3), (4, 3), (1, 1), (5, 3)]))

        position_bucket_2 = dict(((i, 0)
            for i in [(7, 3), (8, 2), (7, 1), (8, 1), (6, 1), (3, 1), (5, 1),
                (4, 1), (7, 2)]))

        for i in range(100):
            new = noiser.uniform_noise(universe.copy(), 1)
            self.assertTrue(new.bots[0].noisy)
            self.assertTrue(new.bots[2].noisy)
            position_bucket_0[new.bots[0].current_pos] += 1
            position_bucket_2[new.bots[2].current_pos] += 1
        self.assertEqual(100, sum(position_bucket_0.itervalues()))
        self.assertEqual(100, sum(position_bucket_2.itervalues()))
        # Since this is a randomized algorithm we need to be a bit lenient with
        # our tests. We check that each position was selected at least once and
        # check that it was selected a minimum of five times.
        for v in position_bucket_0.itervalues():
            self.assertTrue(v != 0)
            self.assertTrue(v >= 5, 'Testing randomized function, may fail sometimes.')

        for v in position_bucket_2.itervalues():
            self.assertTrue(v != 0)
            self.assertTrue(v >= 5, 'Testing randomized function, may fail sometimes.')

    def test_uniform_noise_4_bots_no_noise(self):
        test_layout = (
        """ ##################
            # #.  .  # . 2   #
            # #####    #####3#
            #  0  . #  .  .#1#
            ################## """)
        universe = create_CTFUniverse(test_layout, 4)
        noiser = UniverseNoiser(universe.copy())

        position_bucket_0 = dict(((i, 0)
            for i in [(1, 2), (7, 3), (1, 3), (3, 3), (6, 3),
                (2, 3), (4, 3), (1, 1), (5, 3)]))

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
        # our tests. We check that each position was selected at least once and
        # check that it was selected a minimum of five times.
        for v in position_bucket_0.itervalues():
            self.assertTrue(v != 0)
            self.assertTrue(v >= 5, 'Testing randomized function, may fail sometimes.')

        # bots should never have been noised
        self.assertEqual(100, position_bucket_2[bot_2_pos])

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

        noiser = UniverseNoiser(universe.copy())
        new_uni = noiser.uniform_noise(universe.copy(), 0)
        new_positions = [b.current_pos for b in new_uni.bots]

        # assume not all bots (except 0 and 2) are in the original position anymore
        self.assertEqual(positions[0::2], new_positions[0::2])
        self.assertNotEqual(positions[1::2], new_positions[1::2],
                            "Testing randomized function, may fail sometimes.")


class TestAbstracts(unittest.TestCase):

    def test_AbstractViewer(self):
        av = AbstractViewer()
        self.assertRaises(NotImplementedError, av.observe, None, None, None, None)

    def test_AbstractPlayer(self):
        ap = AbstractPlayer()
        self.assertRaises(NotImplementedError, ap.get_move)

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
        gm.register_team(SimpleTeam(TestPlayer([east, east, east, south, stop, east])))
        gm.register_team(SimpleTeam(TestPlayer([west, west, west, stop, west, west])))

        gm.register_viewer(DevNullViewer())

        gm.set_initial()
        gm.play_round(0)
        test_first_round = (
            """ ######
                # 0. #
                #..1 #
                ###### """)
        self.assertEqual(create_TestUniverse(test_first_round), gm.universe)

        gm.play_round(1)
        test_second_round = (
            """ ######
                # 0. #
                #.1  #
                ###### """)
        self.assertEqual(create_TestUniverse(test_second_round), gm.universe)

        gm.play_round(2)
        test_third_round = (
            """ ######
                #  . #
                #.0 1#
                ###### """)
        self.assertEqual(create_TestUniverse(test_third_round,
            black_score=KILLPOINTS), gm.universe)

        gm.play_round(3)
        test_fourth_round = (
            """ ######
                #0 . #
                #. 1 #
                ###### """)
        self.assertEqual(create_TestUniverse(test_fourth_round,
            black_score=KILLPOINTS, white_score=KILLPOINTS), gm.universe)

        gm.play_round(4)
        test_fifth_round = (
            """ ######
                # 0. #
                #.1  #
                ###### """)
        self.assertEqual(create_TestUniverse(test_fifth_round,
            black_score=KILLPOINTS, white_score=KILLPOINTS), gm.universe)

        print gm.universe.pretty
        gm.play_round(5)
        test_sixth_round = (
            """ ######
                #  0 #
                #.1  #
                ###### """)
        print gm.universe.pretty
        self.assertEqual(create_TestUniverse(test_sixth_round,
            black_score=KILLPOINTS, white_score=KILLPOINTS), gm.universe)


        # now play the full game
        gm = GameMaster(test_start, number_bots, 200)
        gm.register_team(SimpleTeam(TestPlayer([east, east, east, south, stop, east])))
        gm.register_team(SimpleTeam(TestPlayer([west, west, west, stop, west, west])))
        gm.play()
        test_sixth_round = (
            """ ######
                #  0 #
                #.1  #
                ###### """)
        self.assertEqual(create_TestUniverse(test_sixth_round,
            black_score=KILLPOINTS, white_score=KILLPOINTS), gm.universe)

    def test_malicous_player(self):
        free_obj = Free

        class MaliciousPlayer(AbstractPlayer):
            def _get_move(self, universe):
                universe.teams[0].score = 100
                universe.bots[0].current_pos = (2,2)
                universe.maze[0,0] = free_obj
                return (0,0)

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
                # universe should not have been altered
                test_self.assertEqual(original_universe, gm.universe)
                return (0,0)

        gm.register_team(SimpleTeam(MaliciousPlayer()))
        gm.register_team(SimpleTeam(TestMaliciousPlayer()))

        gm.set_initial()
        gm.play_round(0)

        test_self.assertEqual(original_universe, gm.universe)


    def test_viewer_must_not_change_gm(self):
        free_obj = Free

        class MeanViewer(AbstractViewer):
            def set_initial(self, universe):
                universe.teams[1].score = 50

            def observe(self, round_, turn, universe, events):
                universe.teams[0].score = 100
                universe.bots[0].current_pos = (4,4)
                universe.maze[0,0] = free_obj

                events.append(TeamWins(0))
                test_self.assertEqual(len(events), 2)

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
            def observe(self, round_, turn, universe, events):
                # universe should not have been altered
                test_self.assertEqual(original_universe, gm.universe)

                # there should only be a botmoves event
                test_self.assertEqual(len(events), 1)
                test_self.assertEqual(len(events), 1)
                test_self.assertTrue(BotMoves in events)

        gm.register_viewer(MeanViewer())
        gm.register_viewer(TestViewer())

        gm.set_initial()
        gm.play_round(0)

        self.assertEqual(original_universe, gm.universe)

    def test_win_on_timeout_team_0(self):
        test_start = (
            """ ######
                #0 ..#
                #.. 1#
                ###### """)
        # the game lasts two rounds, enough time for bot 1 to eat food
        gm = GameMaster(test_start, 2, 2)
        # bot 1 moves east twice to eat the single food
        gm.register_team(SimpleTeam(TestPlayer([east, east])))
        gm.register_team(SimpleTeam(StoppingPlayer()))

        # this test viewer caches all events lists seen through observe
        class TestViewer(AbstractViewer):
            def __init__(self):
                self.cache = list()
            def observe(self, round_, turn, universe, events):
                self.cache.append(events)

        # run the game
        tv = TestViewer()
        gm.register_viewer(tv)
        gm.set_initial()
        gm.play()

        # check
        self.assertTrue(TeamWins in tv.cache[-1])
        self.assertEqual(tv.cache[-1][0], TeamWins(0))

    def test_win_on_timeout_team_1(self):
        test_start = (
            """ ######
                #0 ..#
                #.. 1#
                ###### """)
        # the game lasts two rounds, enough time for bot 1 to eat food
        gm = GameMaster(test_start, 2, 2)
        gm.register_team(SimpleTeam(StoppingPlayer()))
        # bot 1 moves west twice to eat the single food
        gm.register_team(SimpleTeam(TestPlayer([west, west])))

        # this test viewer caches all events lists seen through observe
        class TestViewer(AbstractViewer):
            def __init__(self):
                self.cache = list()
            def observe(self, round_, turn, universe, events):
                self.cache.append(events)

        # run the game
        tv = TestViewer()
        gm.register_viewer(tv)
        gm.set_initial()
        gm.play()

        # check
        self.assertTrue(TeamWins in tv.cache[-1])
        self.assertEqual(tv.cache[-1][0], TeamWins(1))

    def test_draw_on_timeout(self):
        test_start = (
            """ ######
                #0 . #
                # . 1#
                ###### """)
        # the game lasts one round, and then draws
        gm = GameMaster(test_start, 2, 1)
        # players do nothing
        gm.register_team(SimpleTeam(StoppingPlayer()))
        gm.register_team(SimpleTeam(StoppingPlayer()))

        # this test viewer caches all events lists seen through observe
        class TestViewer(AbstractViewer):
            def __init__(self):
                self.cache = list()
            def observe(self, round_, turn, universe, events):
                self.cache.append(events)

        # run the game
        tv = TestViewer()
        gm.register_viewer(tv)
        gm.set_initial()
        gm.play()

        # check
        self.assertTrue(GameDraw in tv.cache[-1])
        self.assertEqual(tv.cache[-1][0], GameDraw())

    def test_win_on_eating_all(self):
        test_start = (
            """ ######
                #0 . #
                # . 1#
                ###### """
        )
        # the game lasts one round, and then draws
        gm = GameMaster(test_start, 2, 100)
        # players do nothing
        gm.register_team(SimpleTeam(StoppingPlayer()))
        gm.register_team(SimpleTeam(TestPlayer([west, west, west])))

        # this test viewer caches all events lists seen through observe
        class TestViewer(AbstractViewer):
            def __init__(self):
                self.cache = list()
                self.round_ = list()
            def observe(self, round_, turn, universe, events):
                self.cache.append(events)
                self.round_.append(round_)

        # run the game
        tv = TestViewer()
        gm.register_viewer(tv)
        gm.set_initial()
        gm.play()

        # check
        self.assertTrue(TeamWins in tv.cache[-1])
        self.assertEqual(tv.cache[-1].filter_type(TeamWins)[0], TeamWins(1))
        self.assertEqual(tv.round_[-1], 1)

    def test_lose_on_eating_all(self):
        test_start = (
            """ ######
                #0 . #
                # . 1#
                ###### """
        )
        # the game lasts one round, and then draws
        gm = GameMaster(test_start, 2, 100)
        # players do nothing
        gm.register_team(SimpleTeam(StoppingPlayer()))
        gm.register_team(SimpleTeam(TestPlayer([west, west, west])))
        gm.universe.teams[0].score = 2

        # this test viewer caches all events lists seen through observe
        class TestViewer(AbstractViewer):
            def __init__(self):
                self.cache = list()
                self.round_ = list()
            def observe(self, round_, turn, universe, events):
                self.cache.append(events)
                self.round_.append(round_)

        # run the game
        tv = TestViewer()
        gm.register_viewer(tv)
        gm.set_initial()
        gm.play()

        # check
        self.assertEqual(tv.round_[-1], 1)
        self.assertEqual(gm.universe.teams[0].score, 2)
        self.assertEqual(gm.universe.teams[1].score, 1)
        self.assertTrue(TeamWins in tv.cache[-1])
        self.assertEqual(tv.cache[-1].filter_type(TeamWins)[0], TeamWins(0))

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
        gm = GameMaster(test_start, 2, 100)
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
                self.round_ = list()
            def observe(self, round_, turn, universe, events):
                self.cache.append(events)
                self.round_.append(round_)

        # run the game
        tv = TestViewer()
        gm.register_viewer(tv)
        gm.set_initial()

        self.assertEqual(gm.universe.bots[0].current_pos, (1,1))

        gm.play()

        # check
        self.assertEqual(tv.round_[-1], pelita.game_master.MAX_TIMEOUTS - 1)
        self.assertEqual(gm.universe.teams[0].score, 0)
        self.assertEqual(gm.universe.teams[1].score, 0)
        self.assertEqual(gm.universe.bots[0].current_pos, (2,1))
        self.assertTrue(TeamWins in tv.cache[-1])
        self.assertEqual(tv.cache[-1].filter_type(TeamWins)[0], TeamWins(1))
