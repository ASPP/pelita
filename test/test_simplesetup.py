# -*- coding: utf-8 -*-
import unittest
import uuid

import pelita
from pelita.simplesetup import SimpleClient, SimpleServer, SimplePublisher, SimpleSubscriber, bind_socket, extract_port_range
from pelita.player import SimpleTeam, TestPlayer, AbstractPlayer
from pelita.viewer import AsciiViewer, AbstractViewer
from pelita.datamodel import Free
from pelita.game_master import GameMaster
from players import RandomPlayer

import zmq

class TestSimpleSetup(unittest.TestCase):
    def test_bind_socket(self):
        # check that we cannot bind to a stupid address
        address = "ipc:///tmp/pelita-test-bind-socket-%s" % uuid.uuid4()
        context = zmq.Context()
        socket = context.socket(zmq.PUB)
        bind_socket(socket, address)
        self.assertRaises(zmq.ZMQError, bind_socket, socket, "bad-address", '--publish')

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

        class FailingPlayer(object):
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

    def test_remote_viewer_may_not_change_gm(self):
        free_obj = Free

        self.mean_viewer_did_run = False
        class MeanViewer(AbstractViewer):
            def set_initial(self, universe):
                universe.teams[1].score = 50

            def observe(self_, universe, game_state):
                self.mean_viewer_did_run = True

                universe.teams[0].score = 100
                universe.bots[0].current_pos = (4,4)
                universe.maze[0,0] = free_obj

                game_state["team_wins"] = 0

        test_start = (
            """ ######
                #0 . #
                #.. 1#
                ###### """)

        number_bots = 2

        gm = GameMaster(test_start, number_bots, 1)
        gm.register_team(SimpleTeam(TestPlayer([(0,0)])))
        gm.register_team(SimpleTeam(TestPlayer([(0,0)])))

        original_universe = gm.universe.copy()

        self.test_viewer_did_run = False
        test_self = self
        class TestViewer(AbstractViewer):
            def observe(self_, universe, game_state):
                self.test_viewer_did_run = True

                # universe should not have been altered
                test_self.assertEqual(original_universe, gm.universe)

                # there should only be a botmoves event
                test_self.assertEqual(len(game_state["bot_moved"]), 1)
                test_self.assertEqual(len(game_state["bot_moved"]), 1)

        # We need to be able to tell when our subscriber is able to receive
        # new events from the publisher.
        # Due to its completely asynchronous approach, zmq does not even
        # provide built-in methods to check whether two or more sockets
        # are connected, so we have to figure a way to find out.
        # The approach is as follows: When the publisher starts, it
        # sends only ‘sync’ messages without a pause.
        # When a subscriber is finally connected, it will receive this message and
        # set an instance variable (`has_sync`). The main thread checks whether
        # all variables of all subscribers have been set, will stop
        # sending ‘sync’ and move on.
        # No special thread synchronisation or locking is being used. The current
        # code is hopefully simple enough not to include any race conditions.

        class SyncedSubscriber(SimpleSubscriber):
            def sync(self):
                self.has_sync = True

        address = "ipc:///tmp/pelita-publisher-%s" % uuid.uuid4()
        mean_viewer = SyncedSubscriber(MeanViewer(), address)
        test_viewer = SyncedSubscriber(TestViewer(), address)

        # must be threads because we try to access shared state
        # in the mean_viewer_did_run variable
        # (and in a bad way)
        mean_viewer_thread = mean_viewer.autoplay_thread()
        test_viewer_thread = test_viewer.autoplay_thread()

        publisher_viewer = SimplePublisher(address)

        viewers = [mean_viewer, test_viewer]
        while not all(getattr(viewer, "has_sync", False) for viewer in viewers):
            publisher_viewer.socket.send_json({"__action__": "sync"})

        # now we can register it and game_master takes care of sending messages
        gm.register_viewer(publisher_viewer)

        gm.set_initial()
        gm.play()

        # exit our threads
        publisher_viewer.socket.send_json({"__action__": "exit", "__data__": {}})

        # wait until threads stop
        mean_viewer_thread.join()
        test_viewer_thread.join()
        # must close the socket and terminate the context
        # else we may get an assertion failure in zmq
        publisher_viewer.socket.close()
        publisher_viewer.context.term()

        self.assertEqual(original_universe, gm.universe)

        # check, that the code was actually executed
        self.assertTrue(self.mean_viewer_did_run)
        self.assertTrue(self.test_viewer_did_run)

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
