import unittest
from pelita.player import AbstractPlayer, StoppingPlayer, BFSPlayer
from pelita.universe import create_CTFUniverse
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

        universe = create_CTFUniverse(test_layout, 4)
        game_master = GameMaster(test_layout, 4, 200)
        player_0 = StoppingPlayer()
        player_1 = StoppingPlayer()
        player_2 = StoppingPlayer()
        player_3 = StoppingPlayer()
        game_master.register_player(player_0)
        game_master.register_player(player_1)
        game_master.register_player(player_2)
        game_master.register_player(player_3)

        self.assertEqual(universe.bots[0], player_0.me)
        self.assertEqual(universe.bots[1], player_1.me)
        self.assertEqual(universe.bots[2], player_2.me)
        self.assertEqual(universe.bots[3], player_3.me)

        self.assertEqual(universe, player_1.current_uni)
        self.assertEqual([universe.bots[2]], player_0.team_bots)
        self.assertEqual([universe.bots[i] for i in (1, 3)], player_0.enemy_bots)
        self.assertEqual(universe.bots[1].current_pos, player_1.current_pos)
        self.assertEqual(universe.bots[1].initial_pos, player_1.initial_pos)

class TestBFS_Player(unittest.TestCase):

    def test_adjacency(self):
        test_layout = (
        """ ##################
            #0#.  .  # .     #
            # #####    ##### #
            #     . #  .  .#1#
            ################## """)

        game_master = GameMaster(test_layout, 2, 200)
        bfs = BFSPlayer()
        stopping = StoppingPlayer()
        game_master.register_player(bfs)
        game_master.register_player(stopping)
        game_master.register_viewer(AsciiViewer())
        for k,v in bfs.adjacency.items():
            print k, v
        print bfs.bfs_food()
