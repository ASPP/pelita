# -*- coding: utf-8 -*-

import time

from pelita.messaging import actor_of, RemoteConnection
from pelita.actors import ClientActor, ServerActor

from pelita.viewer import AsciiViewer, DevNullViewer
from pelita.ui.tk_viewer import TkViewer

class SimpleServer(object):
    def __init__(self, layout=None, filename=None, players=4, rounds=200):
        if bool(layout) == bool(filename):
            raise ValueError("You must supply exactly one of layout or file.")

        if filename:
            with open(filename) as file:
                self.layout = file.read()
        else:
            self.layout = layout

        self.players = players
        self.rounds = rounds

        self.server = None
        self.remote = None

    def _setup(self):
        self.server = actor_of(ServerActor, "pelita-main")

        self.remote = RemoteConnection().start_listener(host="", port=50007)
        self.remote.register("pelita-main", self.server)
        self.remote.start_all()

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
    def __init__(self, team_name, team):
        self.team_name = team_name
        self.team = team
        self.main_actor = "pelita-main"
        self.host = ""
        self.port = 50007

    def autoplay(self):
        client_actor = ClientActor(self.team_name)
        client_actor.register_team(self.team)

        # Try 3 times to connect
        for i in range(3):
            if client_actor.connect(self.main_actor, self.host, self.port):
                break
            else:
                print "No connection to %s:%s." % (self.host, self.port),
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
            print "Client received CTRL+C. Exiting."
        finally:
            client_actor.actor_ref.stop()

