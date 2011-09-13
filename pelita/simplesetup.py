# -*- coding: utf-8 -*-

""" simplesetup.py defines the SimpleServer and SimpleClient classes
which allow for easy game setup.
"""

import time
import sys
import logging
import multiprocessing
import threading
import signal
import itertools

from .messaging import actor_of, RemoteConnection
from .actors import ClientActor, ServerActor, ViewerActor
from .layout import get_random_layout, get_layout_by_name

from .viewer import AsciiViewer
from .ui.tk_viewer import TkViewer
from .utils.signal_handlers import keyboard_interrupt_handler, exit_handler

_logger = logging.getLogger("pelita.simplesetup")

__docformat__ = "restructuredtext"

def auto_connect(connect_func, retries=10, delay=0.5, silent=True):
     # Try retries times to connect
    if retries is None:
        iter = itertools.count()
    else:
        iter = xrange(retries)
    for i in iter:
        if connect_func():
            return True
        else:

            if retries is None:
                if not silent:
                    sys.stdout.write("[%s]\b\b\b" % "-\\|/"[i % 4])
                time.sleep(delay)
            else:
                if i < retries - 1:
                    if not silent:
                        print " Waiting %i seconds. (%d/%d)" % (delay, i + 1, retries)
                    time.sleep(delay)
    if not silent:
        print "Giving up."
    return False

class SimpleServer(object):
    """ Sets up a simple Server with most settings pre-configured.

    Usage
    -----
        server = SimpleServer(layout_file="mymaze.layout", rounds=3000, port=50007)
        server.run_tk()

    The Parameters 'layout_string', 'layout_name' and 'layout_file' are mutually
    exclusive. If neither is supplied, a layout will be selected at random.

    Parameters
    ----------
    layout_string : string, optional
        The layout as a string.
    layout_name : string, optional
        The name of an available layout
    layout_file : filename, optional
        A file which holds a layout.
    layout_filter : string, optional
        A filter to restrict the pool of random layouts
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

    Raises
    ------
    ValueError:
        if more than one layout keyword is specified
    IOError:
        if layout_file was given, but file does not exist

    """
    def __init__(self, layout_string=None, layout_name=None, layout_file=None,
                 layout_filter = 'normal_without_dead_ends',
                 players=4, rounds=3000, host="", port=50007,
                 local=True, silent=True, dump_to_file=None):

        if (layout_string and layout_name or
                layout_string and layout_file or
                layout_name and layout_file or
                layout_string and layout_name and layout_file):
            raise  ValueError("Can only supply one of: 'layout_string'"+\
                    "'layout_name' or 'layout_file'")
        elif layout_string:
            self.layout = layout_string
        elif layout_name:
            self.layout = get_layout_by_name(layout_name)
        elif layout_file:
            with open(layout_file) as file:
                self.layout = file.read()
        else:
            self.layout = get_random_layout(filter=layout_filter)

        self.players = players
        self.rounds = rounds
        self.silent = silent

        if local:
            self.host = None
            self.port = None
            signal.signal(signal.SIGINT, keyboard_interrupt_handler)
        else:
            self.host = host
            self.port = port

        self.server = None
        self.remote = None

        self.dump_to_file = dump_to_file

        self._startup()

    def stop(self):
        """ Stops the server.
        """
        self.server.stop()
        if self.remote:
            self.remote.stop()

    def _startup(self):
        """ Instantiates the ServerActor and initialises a new game.
        """
        self.server = actor_of(ServerActor, "pelita-main")

        if self.port is not None:
            if not self.silent:
                print "Starting remote connection on %s:%s" % (self.host, self.port)
            self.remote = RemoteConnection().start_listener(host=self.host, port=self.port)
            self.remote.register("pelita-main", self.server)
            self.remote.start_all()
        else:
            if not self.silent:
                print "Starting actor '%s'" % "pelita-main"
            self.server.start()

        # Begin code for automatic closing the server when a game has run
        # TODO: this is bit of a hack and should be done by linking
        # the actors/remote connection.

        if self.dump_to_file:
            self.server.notify("set_dump_file", [self.dump_to_file])

        self.server.notify("set_auto_shutdown", [True])
        if self.port is not None:
            def on_stop():
                print "STOP"
                _logger.info("Automatically stopping remote connection.")
                self.remote.stop()

            self.server._actor.on_stop = on_stop

        # End code for automatic closing

        self.server.notify("initialize_game", [self.layout, self.players, self.rounds])

    def _run_save(self, main_block):
        """ Method which executes `main_block` and rescues
        a possible keyboard interrupt.
        """
        try:
            main_block()
        except KeyboardInterrupt:
            print "Server received CTRL+C. Exiting."
        finally:
            self.server.stop()
            if self.remote:
                self.remote.stop()

            self.server.join(3)

            if self.server.is_alive:
                print "Server did not finish silently. Forcing."
                # TODO This is not nice. We need a better solution
                # for the exit handling issue.
                exit_handler()

    def run_simple(self, viewerclass):
        """ Starts a game with the ASCII viewer.
        This method does not return until the server is stopped.
        """
        def main():
            viewer = viewerclass()
            self.server.notify("register_viewer", [viewer])

            # We wait until the server is dead
            while self.server.is_alive:
                self.server.join(1)

        self._run_save(main)

    def run_tk(self, geometry=None):
        """ Starts a game with the Tk viewer.
        This method does not return until the server or Tk is stopped.
        """
        def main():
            # Register a tk_viewer
            viewer = TkViewer(geometry=geometry)
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

    def _auto_connect(self, client_actor, retries=10, delay=0.5):
        if self.port is None:
            address = "%s" % self.main_actor
            connect = lambda: client_actor.connect_local(self.main_actor)
        else:
            address = "%s on %s:%s" % (self.main_actor, self.host, self.port)
            connect = lambda: client_actor.connect(self.main_actor, self.host, self.port)

        if not auto_connect(connect, retries, delay):
            print "%s: No connection to %s." % (client_actor, address)
            return

        try:
            while client_actor.actor_ref.is_alive:
                if client_actor.is_server_connected() is False:
                    client_actor.actor_ref.stop()
                    client_actor.actor_ref.join(1)
                else:
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
        background_thread.start()
        return background_thread

class SimpleViewer(object):
    def __init__(self, main_actor="pelita-main", host="", port=50007, local=True):
        self.main_actor = main_actor

        if local:
            self.host = None
            self.port = None
        else:
            self.host = host
            self.port = port

        self.viewer_actor = None

    def _auto_connect(self, retries, delay):

        if self.port is None:
            address = "%s" % self.main_actor
            connect = lambda: self.viewer_actor.connect_local(self.main_actor, silent=True)
        else:
            address = "%s on %s:%s" % (self.main_actor, self.host, self.port)
            connect = lambda: self.viewer_actor.connect(self.main_actor, self.host, self.port, silent=True)

        print "%s: Trying to connect to %s." % (self.viewer_actor, address)
        return auto_connect(connect, retries, delay)

    def _run_save(self, main_block, retries, delay):
        """ Method which executes `main_block` and rescues
        a possible keyboard interrupt.
        """

        try:
            if not self._auto_connect(retries, delay):
                return

            main_block()
        except KeyboardInterrupt:
            print "%s received CTRL+C. Exiting." % self
        finally:
            self.viewer_actor.actor_ref.stop()

    def run_tk(self, retries=10, delay=0.5):
        """ Starts a game with the Tk viewer.
        This method does not return until the server or Tk is stopped.
        """
        self.viewer = TkViewer()
        self.viewer_actor = ViewerActor(self.viewer)

        def main():
            # We wait until tk closes
            self.viewer.root.mainloop()

        self._run_save(main, retries, delay)

    def run_ascii(self, retries=10, delay=1):
        """ Starts a game with the ASCII viewer.
        This method does not return until the server is stopped.
        """
        self.viewer = AsciiViewer()
        self.viewer_actor = ViewerActor(self.viewer)

        def main():
            while True:
                time.sleep(1)

        self._run_save(main, retries, delay)
