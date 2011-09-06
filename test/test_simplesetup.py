# -*- coding: utf-8 -*-
import logging
logging.basicConfig()
import unittest

from pelita.simplesetup import SimpleClient, SimpleServer
from pelita.player import SimpleTeam, RandomPlayer

class TestSimpleSetup(unittest.TestCase):
    def test_simple_game(self):
        layout = """
        ##########
        #        #
        #0      1#
        ##########
        """
        client1 = SimpleClient(SimpleTeam("team1", RandomPlayer()))
        client2 = SimpleClient(SimpleTeam("team2", RandomPlayer()))
        server = SimpleServer(layout=layout, rounds=5, players=2)

        self.assertEqual(server.host, None)
        self.assertEqual(server.port, None)
        self.assertTrue(server.server.is_alive)

        server.server.notify("set_auto_shutdown", [True])

        client1.autoplay_background()
        client2.autoplay_background()
        server.run_ascii()

        self.assertFalse(server.server.is_alive)

if __name__ == '__main__':
    unittest.main()
