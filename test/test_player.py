import unittest
from pelita.player import *
from pelita.datamodel import create_CTFUniverse, north, stop, east, west
from pelita.game_master import GameMaster
from pelita.viewer import AsciiViewer

class TestAbstractPlayer(unittest.TestCase):
    def assertUniversesEqual(self, uni1, uni2):
        self.assertEqual(uni1, uni2, '\n' + uni1.pretty + '\n' + uni2.pretty)

    def assertUniversesNotEqual(self, uni1, uni2):
        self.assertNotEqual(uni1, uni2, '\n' + uni1.pretty + '\n' + uni2.pretty)

    def test_convenience(self):

        test_layout = (
        """ ##################
            #0#.  .  # .     #
            #2#####    ####1 #
            #     . #  .  #3##
            ################## """)

        game_master = GameMaster(test_layout, 4, 2, noise=False)
        universe = game_master.universe
        player_0 = StoppingPlayer()
        player_1 = TestPlayer('^<')
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

        self.assertEqual(player_1.current_pos, (15, 2))
        self.assertEqual(player_1.initial_pos, (15, 2))
        self.assertEqual(universe.bots[1].current_pos, (15, 2))
        self.assertEqual(universe.bots[1].initial_pos, (15, 2))

        self.assertEqual(universe.teams[0], player_0.team)
        self.assertEqual(universe.teams[0], player_2.team)
        self.assertEqual(universe.teams[1], player_1.team)
        self.assertEqual(universe.teams[1], player_3.team)

        self.assertEqual(universe.teams[1], player_0.enemy_team)
        self.assertEqual(universe.teams[1], player_2.enemy_team)
        self.assertEqual(universe.teams[0], player_1.enemy_team)
        self.assertEqual(universe.teams[0], player_3.enemy_team)

        self.assertEqual(player_0.enemy_food, universe.enemy_food(player_0.team.index))
        self.assertEqual(player_1.enemy_food, universe.enemy_food(player_1.team.index))
        self.assertEqual(player_2.enemy_food, universe.enemy_food(player_2.team.index))
        self.assertEqual(player_3.enemy_food, universe.enemy_food(player_3.team.index))

        self.assertEqual(player_0.team_food, universe.team_food(player_0.team.index))
        self.assertEqual(player_1.team_food, universe.team_food(player_1.team.index))
        self.assertEqual(player_2.team_food, universe.team_food(player_2.team.index))
        self.assertEqual(player_3.team_food, universe.team_food(player_3.team.index))

        self.assertEqual({(0, 1): (1, 2), (0, 0): (1, 1)},
                player_0.legal_moves)
        self.assertEqual({(0, 1): (15, 3), (0, -1): (15, 1), (0, 0): (15, 2),
                          (1, 0): (16, 2)},
                player_1.legal_moves)
        self.assertEqual({(0, 1): (1, 3), (0, -1): (1, 1), (0, 0): (1, 2)},
                player_2.legal_moves)
        self.assertEqual({(0, -1): (15, 2), (0, 0): (15, 3)},
                player_3.legal_moves)

        self.assertEqual(player_1.current_state["round_index"], None)
        self.assertEqual(player_1.current_state["bot_id"], None)

        game_master.play_round()

        self.assertEqual(player_1.current_pos, (15, 2))
        self.assertEqual(player_1.previous_pos, (15, 2))
        self.assertEqual(player_1.initial_pos, (15, 2))
        self.assertEqual(player_1.current_state["round_index"], 0)
        self.assertEqual(player_1.current_state["bot_id"], 3)
        self.assertEqual(universe.bots[1].current_pos, (15, 1))
        self.assertEqual(universe.bots[1].initial_pos, (15, 2))
        self.assertUniversesEqual(player_1.current_uni, player_1.universe_states[-1])

        game_master.play_round()

        self.assertEqual(player_1.current_pos, (15, 1))
        self.assertEqual(player_1.previous_pos, (15, 2))
        self.assertEqual(player_1.initial_pos, (15, 2))
        self.assertEqual(player_1.current_state["round_index"], 1)
        self.assertEqual(player_1.current_state["bot_id"], 3)
        self.assertEqual(universe.bots[1].current_pos, (14, 1))
        self.assertEqual(universe.bots[1].initial_pos, (15, 2))
        self.assertUniversesNotEqual(player_1.current_uni,
                                     player_1.universe_states[-2])


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
        self.assertEqual(gm.universe.bots[0].current_pos, (3, 1))
        self.assertEqual(gm.universe.bots[1].current_pos, (8, 1))
        self.assertEqual(gm.universe.bots[2].current_pos, (3, 2))
        self.assertEqual(gm.universe.bots[3].current_pos, (8, 2))

    def test_shorthand(self):
        test_layout = (
        """ ############
            #0  .  .   #
            #         1#
            ############ """)
        num_rounds = 5
        gm = GameMaster(test_layout, 2, num_rounds)
        gm.register_team(SimpleTeam(TestPlayer('>v<^-)')))
        gm.register_team(SimpleTeam(TestPlayer('<^>v-)')))
        player0_expected_positions = [(1,1), (2,1), (2,2), (1,2), (1,1)]
        player1_expected_positions = [(10,2), (9,2), (9,1), (10,1), (10,2)]
        gm.set_initial()
        for i in range(num_rounds):
            self.assertEqual(gm.universe.bots[0].current_pos,
                player0_expected_positions[i])
            self.assertEqual(gm.universe.bots[1].current_pos,
                player1_expected_positions[i])
            gm.play_round()

    def test_too_many_moves(self):
        test_layout = (
        """ ############
            #0  .  .  1#
            #2        3#
            ############ """)
        gm = GameMaster(test_layout, 4, 3)
        movements_0 = [east, east]
        movements_1 = [west, west]
        gm.register_team(SimpleTeam(TestPlayer(movements_0), TestPlayer(movements_0)))
        gm.register_team(SimpleTeam(TestPlayer(movements_1), TestPlayer(movements_1)))

        self.assertRaises(ValueError, gm.play)

class TestRoundBasedPlayer(unittest.TestCase):
    def test_round_based_players(self):
        test_layout = (
        """ ############
            #0  .  .  1#
            #2        3#
            ############ """)
        gm = GameMaster(test_layout, 4, 3)
        movements_0 = [east, east]
        movements_1_0 = {0: west, 2: west}
        movements_1_1 = {2: west}
        gm.register_team(SimpleTeam(RoundBasedPlayer(movements_0), RoundBasedPlayer(movements_0)))
        gm.register_team(SimpleTeam(RoundBasedPlayer(movements_1_0), RoundBasedPlayer(movements_1_1)))

        self.assertEqual(gm.universe.bots[0].current_pos, (1, 1))
        self.assertEqual(gm.universe.bots[1].current_pos, (10, 1))
        self.assertEqual(gm.universe.bots[2].current_pos, (1, 2))
        self.assertEqual(gm.universe.bots[3].current_pos, (10, 2))

        gm.play()
        self.assertEqual(gm.universe.bots[0].current_pos, (3, 1))
        self.assertEqual(gm.universe.bots[1].current_pos, (8, 1))
        self.assertEqual(gm.universe.bots[2].current_pos, (3, 2))
        self.assertEqual(gm.universe.bots[3].current_pos, (9, 2))

class TestSeededRandom_Player(unittest.TestCase):
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
        gm = GameMaster(test_layout, 2, 5, seed=20)
        gm.register_team(SimpleTeam(SeededRandomPlayer()))
        gm.register_team(SimpleTeam(SeededRandomPlayer()))
        self.assertEqual(gm.universe.bots[0].current_pos, (4, 4))
        self.assertEqual(gm.universe.bots[1].current_pos, (4 + 7, 4))
        gm.play()

        pos_left_bot = gm.universe.bots[0].current_pos
        pos_right_bot = gm.universe.bots[1].current_pos

        # running again to test seed:
        gm = GameMaster(test_layout, 2, 5, seed=20)
        gm.register_team(SimpleTeam(SeededRandomPlayer()))
        gm.register_team(SimpleTeam(SeededRandomPlayer()))
        gm.play()
        self.assertEqual(gm.universe.bots[0].current_pos, pos_left_bot)
        self.assertEqual(gm.universe.bots[1].current_pos, pos_right_bot)

        # running again with other seed:
        gm = GameMaster(test_layout, 2, 5, seed=200)
        gm.register_team(SimpleTeam(SeededRandomPlayer()))
        gm.register_team(SimpleTeam(SeededRandomPlayer()))
        gm.play()
        # most probably, either the left bot or the right bot or both are at
        # a different position
        self.assertTrue(gm.universe.bots[0].current_pos != pos_left_bot
                     or gm.universe.bots[1].current_pos != pos_right_bot)

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
        gm1 = GameMaster(test_layout, 4, 5, seed=20)
        players_a = [SeededRandomPlayer() for _ in range(4)]

        gm1.register_team(SimpleTeam(players_a[0], players_a[2]))
        gm1.register_team(SimpleTeam(players_a[1], players_a[3]))
        gm1.set_initial()
        random_numbers_a = [player.rnd.randint(0, 10000) for player in players_a]
        # check that each player has a different seed (if randomness allows)
        self.assertEqual(len(set(random_numbers_a)), 4, "Probably not all player seeds were unique.")

        gm2 = GameMaster(test_layout, 4, 5, seed=20)
        players_b = [SeededRandomPlayer() for _ in range(4)]

        gm2.register_team(SimpleTeam(players_b[0], players_b[2]))
        gm2.register_team(SimpleTeam(players_b[1], players_b[3]))
        gm2.set_initial()
        random_numbers_b = [player.rnd.randint(0, 10000) for player in players_b]
        self.assertEqual(random_numbers_a, random_numbers_b)

        gm3 = GameMaster(test_layout, 4, 5, seed=200)
        players_c = [SeededRandomPlayer() for _ in range(4)]

        gm3.register_team(SimpleTeam(players_c[0], players_c[2]))
        gm3.register_team(SimpleTeam(players_c[1], players_c[3]))
        gm3.set_initial()
        random_numbers_c = [player.rnd.randint(0, 10000) for player in players_c]

        self.assertNotEqual(random_numbers_a, random_numbers_c)


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

    def test_path(self):
        test_layout = (
        """ ############
            #  . # .# ##
            # ## #  # ##
            #0#.   .##1#
            ############ """)
        gm = GameMaster(test_layout, 2, 7)
        gm.register_team(SimpleTeam(NQRandomPlayer()))
        gm.register_team(SimpleTeam(NQRandomPlayer()))
        gm.play()
        self.assertEqual(gm.universe.bots[0].current_pos, (4, 3))
        self.assertEqual(gm.universe.bots[1].current_pos, (10, 3))


class TestSpeakingPlayer(unittest.TestCase):
    def test_demo_players(self):
        test_layout = (
        """ ############
            #0 #.  .# 1#
            ############ """)
        gm = GameMaster(test_layout, 2, 1)
        gm.register_team(SimpleTeam(SpeakingPlayer()))
        gm.register_team(SimpleTeam(RandomPlayer()))
        gm.play()
        self.assertTrue(gm.game_state["bot_talk"][0].startswith("Going"))
        self.assertEqual(gm.game_state["bot_talk"][1], "")


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
        """################
           #             1#
           #.     0      .#
           #.     2      .#
           #   #      #  3#
           ################ """)

        game_master = GameMaster(test_layout, 4, 5, noise=False)
        team_1 = SimpleTeam(TestPlayer('><---'),
                            TestPlayer('-><>-'))
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

        game_master.play_round()
        # 0 did not move, 1 tracks None
        # 2 moved east, 3 tracks 2
        self.assertEqual(team_2._players[0].tracking_idx, None)
        self.assertEqual(team_2._players[1].tracking_idx, 2)

        game_master.play_round()
        # 0 did not move, 1 tracks 2
        # 2 did not move, 3 still tracks 2
        self.assertEqual(team_2._players[0].tracking_idx, 2)
        self.assertEqual(team_2._players[1].tracking_idx, 2)

    def test_unreachable_border(self):
        test_layout = (
        """ ############
            #0 .   #. 1#
            ############ """)
        game_master = GameMaster(test_layout, 2, 1, noise=False)

        bfs1 = BasicDefensePlayer()
        bfs2 = BasicDefensePlayer()
        game_master.register_team(SimpleTeam(bfs1))
        game_master.register_team(SimpleTeam(bfs2))
        game_master.set_initial()
        game_master.play()
        self.assertEqual(bfs1.path, [(5, 1), (4, 1), (3, 1)])
        self.assertTrue(bfs2.path is None)


    def test_unreachable_bot(self):
        test_layout = (
        """ ############
            #  .  0#. 1#
            ############ """)
        game_master = GameMaster(test_layout, 2, 1, noise=False)

        bfs2 = BasicDefensePlayer()
        game_master.register_team(SimpleTeam(StoppingPlayer()))
        game_master.register_team(SimpleTeam(bfs2))
        game_master.set_initial()
        game_master.play()
        self.assertTrue(bfs2.path is None)


class TestSimpleTeam(unittest.TestCase):

    class BrokenPlayer_with_nothing(object):
        pass

    class BrokenPlayer_without_set_initial(object):
        def _set_initial(self, universe):
            pass

    class BrokenPlayer_without_get_move(object):
        def _set_initial(self, universe):
            pass

    def test_player_api_methods(self):
        self.assertRaises(TypeError, SimpleTeam,
                          self.BrokenPlayer_with_nothing())
        self.assertRaises(TypeError, SimpleTeam,
                          self.BrokenPlayer_without_set_initial())
        self.assertRaises(TypeError, SimpleTeam,
                          self.BrokenPlayer_without_get_move())

    def test_init(self):
        self.assertRaises(ValueError, SimpleTeam)
        object_which_is_neither_string_nor_team = 5
        self.assertRaises(TypeError, SimpleTeam,
                          object_which_is_neither_string_nor_team)

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
        team1 = SimpleTeam(TestPlayer('^'), TestPlayer('>'))

        dummy_universe.teams[0].bots = [1, 5, 10]
        self.assertRaises(ValueError, team1.set_initial, 0, dummy_universe, {})

        dummy_universe.teams[0].bots = [1, 5]
        team1.set_initial(0, dummy_universe, {})
        self.assertEqual(team1.get_move(1, dummy_universe, {}), {"move": north, "say": ""})
        self.assertEqual(team1.get_move(5, dummy_universe, {}), {"move": east, "say": ""})
        self.assertRaises(KeyError, team1.get_move, 6, dummy_universe, {})

        team2 = SimpleTeam(TestPlayer('^'), TestPlayer('>'))

        team2.set_initial(1, dummy_universe, {})
        self.assertEqual(team2.get_move(1, dummy_universe, {}), {"move": north, "say": ""})
        self.assertRaises(KeyError, team2.get_move, 0, dummy_universe, {})
        self.assertRaises(KeyError, team2.get_move, 2, dummy_universe, {})

class TestAbstracts(unittest.TestCase):
    class BrokenPlayer(AbstractPlayer):
        pass

    def test_AbstractPlayer(self):
        self.assertRaises(TypeError, AbstractPlayer)

    def test_BrokenPlayer(self):
        self.assertRaises(TypeError, self.BrokenPlayer)
