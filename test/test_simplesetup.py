# -*- coding: utf-8 -*-
import unittest

from pelita.simplesetup import SimpleClient, SimpleServer, SimplePublisher, SimpleSubscriber
from pelita.player import SimpleTeam, RandomPlayer, TestPlayer
from pelita.viewer import AsciiViewer, AbstractViewer
from pelita.datamodel import Free
from pelita.game_master import GameMaster

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

        mean_viewer = SyncedSubscriber(MeanViewer(), "ipc:///tmp/pelita-publisher")
        test_viewer = SyncedSubscriber(TestViewer(), "ipc:///tmp/pelita-publisher")

        # must be threads because we try to access shared state
        # in the mean_viewer_did_run variable
        # (and in a bad way)
        mean_viewer_thread = mean_viewer.autoplay_thread()
        test_viewer_thread = test_viewer.autoplay_thread()

        publisher_viewer = SimplePublisher("ipc:///tmp/pelita-publisher")

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

        self.assertEqual(original_universe, gm.universe)

        # check, that the code was actually executed
        self.assertTrue(self.mean_viewer_did_run)
        self.assertTrue(self.test_viewer_did_run)


if __name__ == '__main__':
    unittest.main()
