import unittest
import time
import random
from pelita.player import *
from pelita.datamodel import CTFUniverse, north, south, stop, east, west
from pelita.game_master import GameMaster
from pelita.viewer import AsciiViewer

class TestGameRules(unittest.TestCase):
    def test_double_kill(self):

        test_layout = (
        """ ##########
            #   0   .#
            #   2 1  #
            #.      3#
            ########## """)

        game_master = GameMaster(test_layout, 4, 10, noise=False)
        player_0 = RoundBasedPlayer([south])
        player_1 = RoundBasedPlayer([west, west])
        player_2 = StoppingPlayer()
        player_3 = StoppingPlayer()
        game_master.register_team(SimpleTeam(player_0, player_2))
        game_master.register_team(SimpleTeam(player_1, player_3))
        game_master.set_initial()

        game_master.play_round()

        self.assertEqual(player_0.team.score, 0)
        self.assertEqual(player_1.team.score, 0)
        self.assertEqual(player_2.team.score, 0)
        self.assertEqual(player_3.team.score, 0)

        game_master.play_round()
        game_master.play_round()

        self.assertEqual(player_0.team.score, 5)
        self.assertEqual(player_1.team.score, 0)
        self.assertEqual(player_2.team.score, 5)
        self.assertEqual(player_3.team.score, 0)

