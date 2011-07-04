from pelita.game_master import *
import unittest

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
        self.assertRaises(TypeError, game_master.register_player, 0, BrokenPlayer())

class TestAbstracts(unittest.TestCase):

    def test_AbstractViewer(self):
        av = AbstractViewer()
        self.assertRaises(NotImplementedError, av.observe, None, None, None, None)

    def test_AbstractPlayer(self):
        ap = AbstractPlayer()
        self.assertRaises(NotImplementedError, ap.get_move, None)



