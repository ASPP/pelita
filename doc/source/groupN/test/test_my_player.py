import unittest

from pelita.player import SimpleTeam
from pelita.player import RandomPlayer

from pelita.game_master import GameMaster

from .. import MyPlayer

class MyPlayerTest(unittest.TestCase):
    def test_my_player_is_not_moving(self):
        my_team = SimpleTeam("test", MyPlayer(), MyPlayer())
        test_layout = """
            ############
            # 0 #  # 1 #
            #   #  #   #
            # 2 .  . 3 #
            ############
        """
        teams = [
            # register my_team for bots 0, 2
            my_team,
            # register a pre-defined team as an enemy
            SimpleTeam(RandomPlayer(), RandomPlayer())
        ]

        gm = GameMaster(test_layout, teams, number_bots=4, game_time=5, seed=20)

        # play `game_time` rounds
        gm.play()

        # check the position of my bots
        self.assertEqual(gm.universe.bots[0].current_pos, (2,1))
        self.assertEqual(gm.universe.bots[2].current_pos, (2,3))

if __name__ == "__main__":
    unittest.main()

