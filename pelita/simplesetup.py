# -*- coding: utf-8 -*-

import time
import multiprocessing

from pelita.messaging import actor_of, RemoteConnection
from pelita.actors import ClientActor, ServerActor

from pelita.viewer import AsciiViewer, DevNullViewer
from pelita.ui.tk_viewer import TkViewer

class SimpleServer(object):
    def __init__(self, layout=None, layoutfile=None, players=4, rounds=200, host="", port=50007, local=False):
        if bool(layout) == bool(layoutfile):
            raise ValueError("You must supply exactly one of layout or file.")

        if layoutfile:
            with open(layoutfile) as file:
                self.layout = file.read()
        else:
            self.layout = layout

        self.players = players
        self.rounds = rounds

        if local:
            self.host = None
            self.port = None
        else:
            self.host = host
            self.port = port

        self.server = None
        self.remote = None

    def _setup(self):
        self.server = actor_of(ServerActor, "pelita-main")

        if self.port is not None:
            print "Starting remote connection on %s:%s" % (self.host, self.port)
            self.remote = RemoteConnection().start_listener(host=self.host, port=self.port)
            self.remote.register("pelita-main", self.server)
            self.remote.start_all()
        else:
            print "Starting actor '%s'" % "pelita-main"
            self.server.start()

        self.server.notify("initialize_game", [self.layout, self.players, self.rounds])

    def _run_save(self, main_block):
        """ Method which executes `main_block` and rescues
        a possible keyboard interrupt.
        """
        self._setup()

        try:
            main_block()
        except KeyboardInterrupt:
            print "Server received CTRL+C. Exiting."
        finally:
            self.server.stop()
            if self.remote:
                self.remote.stop()

    def run_ascii(self):
        def main():
            viewer = AsciiViewer()
            self.server.notify("register_viewer", [viewer])

            # We wait until the server is dead
            while self.server._actor.thread.is_alive:
                self.server._actor.thread.join(1)

        self._run_save(main)

    def run_tk(self):
        def main():
            # Register a tk_viewer
            viewer = TkViewer()
            self.server.notify("register_viewer", [viewer])
            # We wait until tk closes
            viewer.app.mainloop()

        self._run_save(main)

class SimpleClient(object):
    def __init__(self, team_name, team, host="", port=50007, local=False):
        self.team_name = team_name
        self.team = team
        self.main_actor = "pelita-main"

        if local:
            self.host = None
            self.port = None
        else:
            self.host = host
            self.port = port

    def autoplay(self):
        client_actor = ClientActor(self.team_name)
        client_actor.register_team(self.team)

        if self.port is None:
            address = "%s" % self.main_actor
            connect = lambda: client_actor.connect_local(self.main_actor)
        else:
            address = "%s on %s:%s" % (self.main_actor, self.host, self.port)
            connect = lambda: client_actor.connect(self.main_actor, self.host, self.port)

        # Try 3 times to connect
        for i in range(3):
            if connect():
                break
            else:
                print "%s: No connection to %s." % (self.team_name, address),
                if i < 2:
                    print " Waiting 3 seconds. (%d/3)" % (i + 1)
                    time.sleep(3)
        else:
            print "Giving up."
            return

        try:
            while client_actor.actor_ref.is_alive:
                client_actor.actor_ref.join(1)
        except KeyboardInterrupt:
            print "%s: Client received CTRL+C. Exiting." % self.team_name
        finally:
            client_actor.actor_ref.stop()

    def autoplay_background(self):
        # We use a multiprocessing because it behaves well with KeyboardInterrupt.
        background_process = multiprocessing.Process(target=self.autoplay)
        background_process.start()
        return background_process
