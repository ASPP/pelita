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

        client1.autoplay_background()
        client2.autoplay_background()
        server.run_ascii()

        self.assertFalse(server.server.is_alive)

    def test_simple_remote_game(self):
        return
        layout = """
        ##########
        #        #
        #0      1#
        ##########
        """
        client1 = SimpleClient(SimpleTeam("team1", RandomPlayer()), local=False)
        client2 = SimpleClient(SimpleTeam("team2", RandomPlayer()), local=False)
        server = SimpleServer(layout=layout, rounds=5, players=2, local=False)

        self.assertEqual(server.host, "")
        self.assertEqual(server.port, 50007)
        self.assertTrue(server.server.is_alive)

        client1.autoplay_background()
        client2.autoplay_background()
        server.run_ascii()

        self.assertFalse(server.server.is_alive)


if __name__ == '__main__':
    unittest.main()
