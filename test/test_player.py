import unittest
from pelita.player import *
from pelita.datamodel import create_CTFUniverse, north, stop, east, west
from pelita.game_master import GameMaster
from pelita.viewer import AsciiViewer

class TestAbstractPlayer(unittest.TestCase):

    def test_convenience(self):

        test_layout = (
        """ ##################
            #0#.  .  # .     #
            #2#####    #####1#
            #     . #  .  .#3#
            ################## """)

        game_master = GameMaster(test_layout, 4, 200, noise=False)
        universe = game_master.universe
        player_0 = StoppingPlayer()
        player_1 = TestPlayer([stop, north])
        player_2 = StoppingPlayer()
        player_3 = StoppingPlayer()
        game_master.register_team(SimpleTeam(player_0, player_2))
        game_master.register_team(SimpleTeam(player_1, player_3))
        game_master.set_initial()

        self.assertEqual(universe.bots[0], player_0.me)
        self.assertEqual(universe.bots[1], player_1.me)
        self.assertEqual(universe.bots[2], player_2.me)
        self.assertEqual(universe.bots[3], player_3.me)

        self.assertEqual(universe, player_1.current_uni)
        self.assertEqual([universe.bots[0]], player_2.other_team_bots)
        self.assertEqual([universe.bots[1]], player_3.other_team_bots)
        self.assertEqual([universe.bots[2]], player_0.other_team_bots)
        self.assertEqual([universe.bots[3]], player_1.other_team_bots)
        self.assertEqual([universe.bots[i] for i in (0, 2)], player_0.team_bots)
        self.assertEqual([universe.bots[i] for i in (1, 3)], player_0.enemy_bots)
        self.assertEqual([universe.bots[i] for i in (1, 3)], player_1.team_bots)
        self.assertEqual([universe.bots[i] for i in (0, 2)], player_1.enemy_bots)
        self.assertEqual([universe.bots[i] for i in (0, 2)], player_2.team_bots)
        self.assertEqual([universe.bots[i] for i in (1, 3)], player_2.enemy_bots)
        self.assertEqual([universe.bots[i] for i in (1, 3)], player_3.team_bots)
        self.assertEqual([universe.bots[i] for i in (0, 2)], player_3.enemy_bots)
        self.assertEqual(universe.bots[1].current_pos, player_1.current_pos)
        self.assertEqual(universe.bots[1].initial_pos, player_1.initial_pos)

        self.assertEqual(universe.teams[0], player_0.team)
        self.assertEqual(universe.teams[0], player_2.team)
        self.assertEqual(universe.teams[1], player_1.team)
        self.assertEqual(universe.teams[1], player_3.team)

        self.assertEqual({(0, 1): (1, 2), (0, 0): (1, 1)},
                player_0.legal_moves)
        self.assertEqual({(0, 1): (16, 3), (0, -1): (16, 1), (0, 0): (16, 2)},
                player_1.legal_moves)
        self.assertEqual({(0, 1): (1, 3), (0, -1): (1, 1), (0, 0): (1, 2)},
                player_2.legal_moves)
        self.assertEqual({(0, -1): (16, 2), (0, 0): (16, 3)},
                player_3.legal_moves)

        game_master.play_round()
        game_master.play_round()
        self.assertEqual(universe, player_1.current_uni)
        self.assertEqual((16, 1), player_1.current_pos)
        self.assertEqual((16, 2), player_1.previous_pos)
        self.assertNotEqual(player_1.current_uni, player_1.universe_states[-2])

class TestTestPlayer(unittest.TestCase):
    def test_test_players(self):
        test_layout = (
        """ ############
            #0  .  .  1#
            #2        3#
            ############ """)
        gm = GameMaster(test_layout, 4, 2)
        movements_0 = [east, east]
        movements_1 = [west, west]
        gm.register_team(SimpleTeam(TestPlayer(movements_0), TestPlayer(movements_0)))
        gm.register_team(SimpleTeam(TestPlayer(movements_1), TestPlayer(movements_1)))

        self.assertEqual(gm.universe.bots[0].current_pos, (1, 1))
        self.assertEqual(gm.universe.bots[1].current_pos, (10, 1))
        self.assertEqual(gm.universe.bots[2].current_pos, (1, 2))
        self.assertEqual(gm.universe.bots[3].current_pos, (10, 2))

        gm.play()
        print gm.universe
        self.assertEqual(gm.universe.bots[0].current_pos, (3, 1))
        self.assertEqual(gm.universe.bots[1].current_pos, (8, 1))
        self.assertEqual(gm.universe.bots[2].current_pos, (3, 2))
        self.assertEqual(gm.universe.bots[3].current_pos, (8, 2))

class TestNQRandom_Player(unittest.TestCase):
    def test_demo_players(self):
        test_layout = (
        """ ############
            #0#.   .# 1#
            ############ """)
        gm = GameMaster(test_layout, 2, 1)
        gm.register_team(SimpleTeam(NQRandomPlayer()))
        gm.register_team(SimpleTeam(NQRandomPlayer()))
        gm.play()
        self.assertEqual(gm.universe.bots[0].current_pos, (1, 1))
        self.assertEqual(gm.universe.bots[1].current_pos, (9, 1))

class TestBFS_Player(unittest.TestCase):

    def test_demo_players(self):
        test_layout = (
        """ ##################
            #0#.  .  # .     #
            #2#####    #####3#
            #     . #  .  .#1#
            ################## """)
        gm = GameMaster(test_layout, 4, 200)
        gm.register_team(SimpleTeam(StoppingPlayer(), NQRandomPlayer()))
        gm.register_team(SimpleTeam(RandomPlayer(), BFSPlayer()))
        gm.play()

    def test_adjacency_bfs(self):
        test_layout = (
        """ ##################
            #0#.  .  # .     #
            # #####    ##### #
            #     . #  .  .#1#
            ################## """)
        game_master = GameMaster(test_layout, 2, 200)
        bfs = BFSPlayer()
        stopping = StoppingPlayer()
        game_master.register_team(SimpleTeam(bfs))
        game_master.register_team(SimpleTeam(stopping))
        game_master.set_initial()
        path_target = [(11, 3), (10, 3), (10, 2), (9, 2), (8, 2), (7, 2), (7,
            3), (6, 3), (5, 3), (4, 3), (3, 3), (2, 3), (1, 3), (1,2)]
        self.assertEqual(path_target, bfs.current_path)
        for i in range(len(path_target)):
            path_target.pop()
            game_master.play_round()
            self.assertEqual(path_target, bfs.current_path)
        game_master.play_round()
        self.assertEqual([(14, 3), (13, 3)], bfs.current_path)
        game_master.play_round()
        self.assertEqual([(14, 3)], bfs.current_path)
        game_master.play_round()
        self.assertEqual([], bfs.current_path)

    def test_unreachable(self):
        test_layout = (
        """ ############
            #0.     #.1#
            ############ """)
        game_master = GameMaster(test_layout, 2, 200)

        bfs1 = BFSPlayer()
        bfs2 = BFSPlayer()
        game_master.register_team(SimpleTeam(bfs1))
        game_master.register_team(SimpleTeam(bfs2))
        game_master.set_initial()
        game_master.play_round()
        self.assertEqual(0, len(bfs1.current_path))
        self.assertEqual(0, len(bfs2.current_path))

class TestBasicDefensePlayer(unittest.TestCase):
    def test_tracking(self):
        test_layout = (
        """##############
           #           1#
           #.    0     .#
           #.    2     .#
           #   #    #  3#
           ############## """)

        game_master = GameMaster(test_layout, 4, 5, noise=False)
        team_1 = SimpleTeam(TestPlayer([stop, stop, west, east]),
                            TestPlayer([ stop, west, east, stop]))
        team_2 = SimpleTeam(BasicDefensePlayer(), BasicDefensePlayer())

        game_master.register_team(team_1)
        game_master.register_team(team_2)
        game_master.set_initial()

        game_master.play_round()
        # 0 moved east, 1 tracks 0
        # 2 did not move, 3 tracks 0
        self.assertEqual(team_2._players[0].tracking_idx, 0)
        self.assertEqual(team_2._players[1].tracking_idx, 0)

        game_master.play_round()
        # 0 moved back, 1 tracks None
        # 2 moved east, 3 tracks 2
        self.assertEqual(team_2._players[0].tracking_idx, None)
        self.assertEqual(team_2._players[1].tracking_idx, 2)

        game_master.play_round()
        # 0 did not move, 1 tracks 2
        # 2 moved back, 3 tracks None
        self.assertEqual(team_2._players[0].tracking_idx, 2)
        self.assertEqual(team_2._players[1].tracking_idx, None)


class TestSimpleTeam(unittest.TestCase):

    def test_simple_team(self):
        class BrokenPlayer(AbstractPlayer):
            pass
        self.assertRaises(TypeError, SimpleTeam, BrokenPlayer())

    def test_init(self):
        self.assertRaises(ValueError, SimpleTeam)
        object_which_is_neither_string_nor_team = 5
        self.assertRaises(AttributeError, SimpleTeam, object_which_is_neither_string_nor_team)

        team0 = SimpleTeam("my team")
        self.assertEqual(team0.team_name, "my team")
        self.assertEqual(len(team0._players), 0)

        team1 = SimpleTeam("my team", TestPlayer([]))
        self.assertEqual(team1.team_name, "my team")
        self.assertEqual(len(team1._players), 1)

        team2 = SimpleTeam("my other team", TestPlayer([]), TestPlayer([]))
        self.assertEqual(team2.team_name, "my other team")
        self.assertEqual(len(team2._players), 2)

        team3 = SimpleTeam(TestPlayer([]))
        self.assertEqual(team3.team_name, "")
        self.assertEqual(len(team3._players), 1)

        team4 = SimpleTeam(TestPlayer([]), TestPlayer([]))
        self.assertEqual(team4.team_name, "")
        self.assertEqual(len(team4._players), 2)

    def test_bot_ids(self):
        layout = (
            """ ####
                #01#
                #### """
        )
        dummy_universe = create_CTFUniverse(layout, 2)
        team1 = SimpleTeam(TestPlayer([north]), TestPlayer([east]))

        self.assertRaises(ValueError, team1._set_bot_ids, [1, 5, 10])
        team1._set_bot_ids([1,5])

        team1._set_initial(dummy_universe)
        self.assertEqual(team1._get_move(1, dummy_universe), north)
        self.assertEqual(team1._get_move(5, dummy_universe), east)
        self.assertRaises(KeyError, team1._get_move, 6, dummy_universe)

        team2 = SimpleTeam(TestPlayer([north]), TestPlayer([east]))
        team2._set_bot_ids([1])

        team2._set_initial(dummy_universe)
        self.assertEqual(team2._get_move(1, dummy_universe), north)
        self.assertRaises(KeyError, team2._get_move, 0, dummy_universe)
        self.assertRaises(KeyError, team2._get_move, 2, dummy_universe)

