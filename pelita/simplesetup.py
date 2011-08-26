# -*- coding: utf-8 -*-

""" simplesetup.py defines the SimpleServer and SimpleClient classes
which allow for easy game setup.
"""

import time
import multiprocessing
import threading
import signal

from pelita.messaging import actor_of, RemoteConnection
from pelita.actors import ClientActor, ServerActor
from pelita.layout import get_random_layout

from pelita.viewer import AsciiViewer
from pelita.ui.tk_viewer import TkViewer
from pelita.utils.signal_handlers import keyboard_interrupt_handler


__docformat__ = "restructuredtext"



class SimpleServer(object):
    """ Sets up a simple Server with most settings pre-configured.

    Usage
    -----
        server = SimpleServer(layoutfile="mymaze.layout", rounds=3000, port=50007)
        server.run_tk()

    Parameters
    ----------
    layout : string, optional
        The layout as a string. If missing, a `layoutfile` must be given.
    layoutfile : filename, optional
        A file which holds a layout. If missing, a `layout` must be given.
    players : int, optional
        The number of Players/Bots used in the layout. Default: 4.
    rounds : int, optional
        The number of rounds played. Default: 3000.
    host : string, optional
        The hostname which the server runs on. Default: "".
    port : int, optional
        The port which the server runs on. Default: 50007.
    local : boolean, optional
        If True, we only setup a local server. Default: True.
    """
    def __init__(self, layout=None, layoutfile=None, players=4, rounds=3000, host="", port=50007, local=True):

        if layout is None:
            if layoutfile:
                with open(layoutfile) as file:
                    self.layout = file.read()
            else:
                self.layout = get_random_layout()
        else:
            self.layout = layout

        self.players = players
        self.rounds = rounds

        if local:
            self.host = None
            self.port = None
            signal.signal(signal.SIGINT, keyboard_interrupt_handler)
        else:
            self.host = host
            self.port = port

        self.server = None
        self.remote = None

    def _setup(self):
        """ Instantiates the ServerActor and initialises a new game.
        """
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
        """ Starts a game with the ASCII viewer.
        This method does not return until the server is stopped.
        """
        def main():
            viewer = AsciiViewer()
            self.server.notify("register_viewer", [viewer])

            # We wait until the server is dead
            while self.server._actor.thread.is_alive:
                self.server._actor.thread.join(1)

        self._run_save(main)

    def run_tk(self):
        """ Starts a game with the Tk viewer.
        This method does not return until the server or Tk is stopped.
        """
        def main():
            # Register a tk_viewer
            viewer = TkViewer()
            self.server.notify("register_viewer", [viewer])
            # We wait until tk closes
            viewer.root.mainloop()

        self._run_save(main)

class SimpleClient(object):
    """ Sets up a simple Client with most settings pre-configured.

    Usage
    -----
        client = SimpleClient(SimpleTeam("the good ones", BFSPlayer(), NQRandomPlayer()))
        # client.host = "pelita.server.example.com"
        # client.port = 50011
        client.autoplay()

    Parameters
    ----------
    team: PlayerTeam
        A PlayerTeam instance which defines the algorithms for each Bot.
    team_name : string
        The name of the team. (optional, if not defined in team)
    host : string, optional
        The hostname which the server runs on. Default: "".
    port : int, optional
        The port which the server runs on. Default: 50007.
    local : boolean, optional
        If True, we only connect to a local server. Default: True.
    """
    def __init__(self, team, team_name="", host="", port=50007, local=True):
        self.team = team

        if hasattr(self.team, "team_name"):
            self.team_name = self.team.team_name

        if team_name:
            self.team_name = team_name

        self.main_actor = "pelita-main"

        if local:
            self.host = None
            self.port = None
        else:
            self.host = host
            self.port = port

    def _auto_connect(self, client_actor, retries=3, delay=3):
        if self.port is None:
            address = "%s" % self.main_actor
            connect = lambda: client_actor.connect_local(self.main_actor)
        else:
            address = "%s on %s:%s" % (self.main_actor, self.host, self.port)
            connect = lambda: client_actor.connect(self.main_actor, self.host, self.port)

        # Try retries times to connect
        for i in range(retries):
            if connect():
                break
            else:
                print "%s: No connection to %s." % (client_actor, address)
                if i < retries - 1:
                    print " Waiting %f seconds. (%d/%d)" % (delay, i + 1, retries)
                    time.sleep(delay)
        else:
            print "Giving up."
            return

        try:
            while client_actor.actor_ref.is_alive:
                client_actor.actor_ref.join(1)
        except KeyboardInterrupt:
            print "%s: Client received CTRL+C. Exiting." % client_actor
        finally:
            client_actor.actor_ref.stop()

    def autoplay(self):
        """ Creates a new ClientActor, and connects it with
        the Server.
        This method only returns when the ClientActor finishes.
        """
        client_actor = ClientActor(self.team_name)
        client_actor.register_team(self.team)

        self._auto_connect(client_actor)

    def autoplay_background(self):
        """ Calls self.autoplay() but stays in the background.

        Useful for defining both server and client in the same Python script.
        For standalone clients, the normal autoplay method is sufficient.
        """
        if self.port is None:
            self.autoplay_thread()
        else:
            self.autoplay_process()

    def autoplay_process(self):
        # We use a multiprocessing because it behaves well with KeyboardInterrupt.
        background_process = multiprocessing.Process(target=self.autoplay)
        background_process.start()
        return background_process

    def autoplay_thread(self):
        # We cannot use multiprocessing in a local game.
        # Or that is, we cannot until we also use multiprocessing Queues.
        background_thread = threading.Thread(target=self.autoplay)
        background_thread.daemon = True
        background_thread.start()
        return background_thread
