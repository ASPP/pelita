import unittest
import uuid

import zmq

import pelita
from pelita.player import AbstractPlayer, SimpleTeam, TestPlayer
from pelita.simplesetup import SimpleClient, SimpleServer, bind_socket, extract_port_range
from players import RandomPlayer


class TestSimpleSetup(unittest.TestCase):
    def test_bind_socket(self):
        # check that we cannot bind to a stupid address
        address = "ipc:///tmp/pelita-test-bind-socket-%s" % uuid.uuid4()
        context = zmq.Context()
        socket = context.socket(zmq.PUB)
        bind_socket(socket, address)
        self.assertRaises(zmq.ZMQError, bind_socket, socket, "bad-address", '--publish')
        socket.close()

    def test_simple_game(self):
        layout = """
        ##########
        #        #
        #0  ..  1#
        ##########
        """
        server = SimpleServer(layout_string=layout, rounds=5, players=2,
                              bind_addrs=("ipc:///tmp/pelita-testplayer1-%s" % uuid.uuid4(),
                                          "ipc:///tmp/pelita-testplayer2-%s" % uuid.uuid4()))

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
        #0  ..  1#
        ##########
        """
        server = SimpleServer(layout_string=layout, rounds=5, players=2)

        for bind_address in server.bind_addresses:
            self.assertTrue(bind_address.startswith("tcp://"))

        client1_address = server.bind_addresses[0].replace("*", "localhost")
        client2_address = server.bind_addresses[1].replace("*", "localhost")

        client1 = SimpleClient(SimpleTeam("team1", TestPlayer("^>>v<")), address=client1_address)
        client2 = SimpleClient(SimpleTeam("team2", TestPlayer("^<<v>")), address=client2_address)

        client1.autoplay_process()
        client2.autoplay_process()
        server.run()
        server.shutdown()

    def test_simple_failing_bots(self):
        layout = """
        ##########
        #        #
        #0  ..  1#
        ##########
        """
        server = SimpleServer(layout_string=layout, rounds=5, players=2)

        for bind_address in server.bind_addresses:
            self.assertTrue(bind_address.startswith("tcp://"))

        client1_address = server.bind_addresses[0].replace("*", "localhost")
        client2_address = server.bind_addresses[1].replace("*", "localhost")

        class FailingPlayer:
            def _set_initial(self, dummy, dummy2):
                pass
            def _set_index(self, dummy):
                pass
            def _get_move(self, universe, game_state):
                pass

        client1 = SimpleClient(SimpleTeam("team1", TestPlayer("^>>v<")), address=client1_address)
        client2 = SimpleClient(SimpleTeam("team2", FailingPlayer()), address=client2_address)

        client1.autoplay_process()
        client2.autoplay_process()
        server.run()
        server.shutdown()

    def test_failing_bots_do_not_crash_server_in_set_initial(self):
        layout = """
        ##########
        #        #
        #0  ..  1#
        ##########
        """
        server = SimpleServer(layout_string=layout, rounds=5, players=2, timeout_length=0.3)

        for bind_address in server.bind_addresses:
            self.assertTrue(bind_address.startswith("tcp://"))

        client1_address = server.bind_addresses[0].replace("*", "localhost")
        client2_address = server.bind_addresses[1].replace("*", "localhost")

        class ThisIsAnExpectedException(Exception):
            pass

        class FailingPlayer(AbstractPlayer):
            def set_initial(self):
                raise ThisIsAnExpectedException()

            def get_move(self):
                raise ThisIsAnExpectedException()

        old_timeout = pelita.simplesetup.DEAD_CONNECTION_TIMEOUT
        pelita.simplesetup.DEAD_CONNECTION_TIMEOUT = 0.3

        client1 = SimpleClient(SimpleTeam("team1", FailingPlayer()), address=client1_address)
        client2 = SimpleClient(SimpleTeam("team2", FailingPlayer()), address=client2_address)

        client1.autoplay_process()
        client2.autoplay_process()
        server.run()
        server.shutdown()

        pelita.simplesetup.DEAD_CONNECTION_TIMEOUT = old_timeout

    def test_failing_bots_do_not_crash_server(self):
        layout = """
        ##########
        #        #
        #0  ..  1#
        ##########
        """
        server = SimpleServer(layout_string=layout, rounds=5, players=2, timeout_length=0.3)

        for bind_address in server.bind_addresses:
            self.assertTrue(bind_address.startswith("tcp://"))

        client1_address = server.bind_addresses[0].replace("*", "localhost")
        client2_address = server.bind_addresses[1].replace("*", "localhost")

        class ThisIsAnExpectedException(Exception):
            pass

        class FailingPlayer(AbstractPlayer):
            def get_move(self):
                raise ThisIsAnExpectedException()
        old_timeout = pelita.simplesetup.DEAD_CONNECTION_TIMEOUT
        pelita.simplesetup.DEAD_CONNECTION_TIMEOUT = 0.3

        client1 = SimpleClient(SimpleTeam("team1", FailingPlayer()), address=client1_address)
        client2 = SimpleClient(SimpleTeam("team2", FailingPlayer()), address=client2_address)

        client1.autoplay_process()
        client2.autoplay_process()
        server.run()
        server.shutdown()

        pelita.simplesetup.DEAD_CONNECTION_TIMEOUT = old_timeout

    def test_extract_port_range(self):
        test_cases = [
            ("tcp://*",                     dict(addr="tcp://*")),
            ("tcp://*:",                    dict(addr="tcp://*:")),
            ("tcp://*:*",                   dict(addr="tcp://*", port_min=None, port_max=None)),
            ("tcp://*:123",                 dict(addr="tcp://*:123")),
            ("tcp://*:[123:124]",           dict(addr="tcp://*", port_min=123, port_max=124)),
            ("tcp://*:123:[124:125]]",      dict(addr="tcp://*:123", port_min=124, port_max=125)),
            ("tcp://*:123[124:125]]",       dict(addr="tcp://*:123[124:125]]")),
            ("ipc:///tmp/pelita-publisher", dict(addr="ipc:///tmp/pelita-publisher"))
        ]

        for test in test_cases:
            extracted = extract_port_range(test[0])
            self.assertEqual(extracted, test[1])

if __name__ == '__main__':
    unittest.main()
