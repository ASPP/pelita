# -*- coding: utf-8 -*-
import logging
logging.basicConfig()
import unittest

from pelita.simplesetup import SimpleClient, SimpleServer
from pelita.player import SimpleTeam, RandomPlayer

class TestSimpleSetup(unittest.TestCase):

    def test_load_layout(self):
        # check that using the old API raises an error
        self.assertRaises(TypeError, SimpleServer, layout="")
        # check that too many layout args raise an error
        layout_string = """
        ##########
        #2      3#
        #0      1#
        ##########
        """
        layout_name = "layout_01_demo"
        layout_file = "test/test_layout.layout"
        self.assertRaises(ValueError, SimpleServer,
                layout_string=layout_string,
                layout_name=layout_name)
        self.assertRaises(ValueError, SimpleServer,
                layout_string=layout_string,
                layout_file=layout_file)
        self.assertRaises(ValueError, SimpleServer,
                layout_name=layout_name,
                layout_file=layout_file)
        self.assertRaises(ValueError, SimpleServer,
                layout_string=layout_string,
                layout_name=layout_name,
                layout_file=layout_file)
        # check that unknown layout_name raises an appropriate error
        self.assertRaises(ValueError, SimpleServer, layout_name="foobar")
        # check that a non existent file raises an error
        self.assertRaises(IOError, SimpleServer, layout_file="foobar")
        # check that stuff behaves as it should
        SimpleServer()
        SimpleServer(layout_string=layout_string)
        SimpleServer(layout_name=layout_name)
        SimpleServer(layout_file=layout_file)

    def test_simple_game(self):
        layout = """
        ##########
        #        #
        #0      1#
        ##########
        """
        client1 = SimpleClient(SimpleTeam("team1", RandomPlayer()))
        client2 = SimpleClient(SimpleTeam("team2", RandomPlayer()))
        server = SimpleServer(layout_string=layout, rounds=5, players=2)

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
