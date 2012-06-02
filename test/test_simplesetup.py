# -*- coding: utf-8 -*-
import unittest

from pelita.simplesetup import SimpleClient, SimpleServer
from pelita.player import SimpleTeam, RandomPlayer
from pelita.viewer import AsciiViewer

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
        layout_name = "layout_normal_with_dead_ends_001"
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
        SimpleServer().shutdown()
        SimpleServer(layout_string=layout_string).shutdown()
        SimpleServer(layout_name=layout_name).shutdown()
        SimpleServer(layout_file=layout_file, players=2).shutdown()

    def test_simple_game(self):
        layout = """
        ##########
        #        #
        #0      1#
        ##########
        """
        server = SimpleServer(layout_string=layout, rounds=5, players=2,
                              bind_addrs=("ipc:///tmp/pelita-testplayer1",
                                          "ipc:///tmp/pelita-testplayer2"))

        for bind_address in server.bind_addresses:
            self.assertTrue(bind_address.startswith("ipc://"))

        client1_address = server.bind_addresses[0]
        client2_address = server.bind_addresses[1]

        client1 = SimpleClient(SimpleTeam("team1", RandomPlayer()), address=client1_address)
        client2 = SimpleClient(SimpleTeam("team2", RandomPlayer()), address=client2_address)

        client1.autoplay_process()
        client2.autoplay_process()
        server.run()
        server.shutdown()

    def test_simple_remote_game(self):
        layout = """
        ##########
        #        #
        #0      1#
        ##########
        """
        server = SimpleServer(layout_string=layout, rounds=5, players=2)

        for bind_address in server.bind_addresses:
            self.assertTrue(bind_address.startswith("tcp://"))

        client1_address = server.bind_addresses[0].replace("*", "localhost")
        client2_address = server.bind_addresses[1].replace("*", "localhost")

        client1 = SimpleClient(SimpleTeam("team1", RandomPlayer()), address=client1_address)
        client2 = SimpleClient(SimpleTeam("team2", RandomPlayer()), address=client2_address)

        client1.autoplay_process()
        client2.autoplay_process()
        server.run()
        server.shutdown()

if __name__ == '__main__':
    unittest.main()
