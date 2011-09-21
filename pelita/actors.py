# -*- coding: utf-8 -*-

""" Actor classes which allow for transparent communication
between GameMaster and client Teams over the network.
"""

import sys
import Queue

import logging
import time
from pelita.viewer import DumpingViewer

_logger = logging.getLogger("pelita")
_logger.setLevel(logging.DEBUG)

from .messaging import (DispatchingActor, expose, actor_registry,
                        actor_of, RemoteConnection, DeadConnection,
                        ActorNotRunning)
from .messaging.remote_actor import RemoteActorReference
from .game_master import (GameMaster, PlayerTimeout, PlayerDisconnected,
                          AbstractViewer)

__docformat__ = "restructuredtext"

TIMEOUT = 3

def get_server_actor(name, host=None, port=None):
    try:
        if port is None:
            # assume local game
            server_actor = actor_registry.get_by_name(name)
        else:
            server_actor = RemoteConnection().actor_for(name, host, port)
    except DeadConnection:
        # no connection could be established
        server_actor = None

    return server_actor


class _ViewerActor(DispatchingActor):
    """ Actor used to communicate with
    """
    def on_start(self):
        self._server = None
        self._viewer = None

    @expose
    def set_viewer(self, viewer):
        self._viewer = viewer

    @expose
    def set_initial(self, universe):
        self._viewer.set_initial(universe)

    @expose
    def observe(self, round_, turn, universe, events):
        self._viewer.observe(round_, turn, universe, events)

    @expose
    def connect(self, main_actor, timeout, host=None, port=None):
        self._server = get_server_actor(main_actor, host, port)
        if not self._server:
            self.ref.reply("failed")
            return

        try:
            if self._server.query("register_viewer_actor", [self.ref.uuid]).get(timeout) == "ok":
                _logger.info("Connection accepted")
                self.ref.reply("ok")
        except Queue.Empty:
            self.ref.reply("actor no reply")
        except ActorNotRunning:
            # local server is not yet running. Try again later
            self.ref.reply("actor not running")

class ViewerActor(object):
    def __init__(self, viewer):
        self.actor_ref = actor_of(_ViewerActor)
        self.actor_ref._actor.thread.daemon = True # TODO remove this line
        self.actor_ref.start()
        self._set_viewer(viewer)

    def _set_viewer(self, viewer):
        self.actor_ref.notify("set_viewer", [viewer])

    def connect_local(self, main_actor, silent=True):
        """ Tells our local actor to establish a local connection
        with other local actor `main_actor`.
        """
        return self.connect(main_actor, None, None, silent=silent)

    def connect(self, main_actor, host="", port=50007, silent=True):
        """ Tells our local actor to establish a connection with `main_actor`.
        """
        if port is None:
            if not silent:
                print "Trying to establish a connection with local actor '%s'..." % main_actor,
        else:
            if not silent:
                print "Trying to establish a connection with remote actor '%s'..." % main_actor,
        sys.stdout.flush()

        try:
            res = self.actor_ref.query("connect", [main_actor, 2, host, port]).get(TIMEOUT)
            if not silent:
                print res
            if res == "ok":
                return True
        except Queue.Empty:
            if not silent:
                print "failed due to timeout in actor."
        return False

class _ClientActor(DispatchingActor):
    """ Actor used to communicate with the Server.
    """
    def on_start(self):
        self.team = None
        self.server_actor = None

    @expose
    def is_server_connected(self):
        if isinstance(self.server_actor, RemoteActorReference):
            self.ref.reply(self.server_actor.is_connected())
        else:
            self.ref.reply(self.server_actor.is_alive)

    @expose
    def register_team(self, team):
        """ We register the team.
        """
        # TODO: Maybe throw an exception, if a team
        # is already registered.
        # Also: investigate how to deal with concurrency issues
        self.team = team
        self.ref.reply("OK")

    @expose
    def say_hello(self, main_actor, team_name, host=None, port=None):
        """ Opens a connection to the remote main_actor,
        and sends it a "hello" message with the given team_name.
        """

        self.server_actor = get_server_actor(main_actor, host, port)
        if not self.server_actor:
            self.ref.reply("failed")
            return

        try:
            if self.server_actor.query("hello", [team_name, self.ref.uuid]).get(2) == "ok":
                _logger.info("Connection accepted")
                self.ref.reply("ok")
        except Queue.Empty:
            self.ref.reply("actor no reply")
        except ActorNotRunning:
            # local server is not yet running. Try again later
            self.ref.reply("actor not running")

    @expose
    def set_bot_ids(self, *bot_ids):
        """ Called by the server. This method sets the available bot_ids for this team.
        """
        self.ref.reply(self.team._set_bot_ids(bot_ids))

    @expose
    def set_initial(self, universe):
        """ Called by the server. This method tells us the initial universe.
        """
        self.ref.reply(self.team._set_initial(universe))

    @expose
    def play_now(self, bot_index, universe):
        """ Called by the server. This message requests a new move
        from the bot with index `bot_index`.
        """
        move = self.team._get_move(bot_index, universe)
        self.ref.reply(move)


class ClientActor(object):
    """ Helper class which makes accessing the _ClientActor easier.

    Parameters
    ----------
    team_name : string
        The name of the team

    Attributes
    ----------
    actor_ref : ActorReference
        The reference to the local _ClientActor
    """
    def __init__(self, team_name):
        self.team_name = team_name

        self.actor_ref = actor_of(_ClientActor)
        self.actor_ref._actor.thread.daemon = True # TODO remove this line
        self.actor_ref.start()

    def is_server_connected(self):
        try:
            return self.actor_ref.query("is_server_connected").get()
        except Queue.Empty:
            return None

    def register_team(self, team):
        """ Registers a team with our local actor.

        Parameters
        ----------
        team : PlayerTeam
            The PlayerTeam which handles all get_move requests.
        """
        self.actor_ref.query("register_team", [team]).get()

    def connect_local(self, main_actor, silent=True):
        """ Tells our local actor to establish a local connection
        with other local actor `main_actor`.
        """
        return self.connect(main_actor, None, None, silent=silent)

    def connect(self, main_actor, host="", port=50007, silent=True):
        """ Tells our local actor to establish a connection with `main_actor`.
        """
        if port is None:
            if not silent:
                print "Trying to establish a connection with local actor '%s'..." % main_actor,
        else:
            if not silent:
                print "Trying to establish a connection with remote actor '%s'..." % main_actor,
        if not silent:
            sys.stdout.flush()

        try:
            res = self.actor_ref.query("say_hello", [main_actor, self.team_name, host, port]).get(TIMEOUT)
            if not silent:
                print res
            if res == "ok":
                return True
        except Queue.Empty:
            if not silent:
                print "failed due to timeout in actor."
        return False

    def __repr__(self):
        return "ClientActor(%s, %s)" % (self.team_name, self.actor_ref)


class RemoteViewer(AbstractViewer):
    def __init__(self, reference):
        self.ref = reference

    def set_initial(self, universe):
        self.ref.notify("set_initial", [universe])

    def observe(self, round_, turn, universe, events):
        self.ref.notify("observe", [round_, turn, universe, events])


class RemoteTeamPlayer(object):
    """ This class is registered with the GameMaster and
    relays all get_move requests to the given ActorReference.
    This can be a local or a remote actor.

    It also does some basic checks for correct return values.

    Parameters
    ----------
    reference : ActorReference
        A reference to the local or remote actor.
    """
    def __init__(self, reference):
        self.ref = reference

    def _set_bot_ids(self, bot_ids):
        try:
            return self.ref.query("set_bot_ids", bot_ids).get(TIMEOUT)
        except (Queue.Empty, ActorNotRunning, DeadConnection):
            pass

    def _set_initial(self, universe):
        try:
            return self.ref.query("set_initial", [universe]).get(TIMEOUT)
        except (Queue.Empty, ActorNotRunning, DeadConnection):
            pass

    def _get_move(self, bot_idx, universe):
        try:
            result = self.ref.query("play_now", [bot_idx, universe]).get(TIMEOUT)
            return tuple(result)
        except TypeError:
            # if we could not convert into a tuple (e.g. bad reply)
            return None
        except Queue.Empty:
            # if we did not receive a message in time
            raise PlayerTimeout()
        except (ActorNotRunning, DeadConnection):
            # if the remote connection is closed
            raise PlayerDisconnected()

class ServerActor(DispatchingActor):
    """ Actor which is used to handle all incoming requests,
    assigns each team a RemoteTeamPlayer and registers this with
    GameMaster.

    It also automatically starts a new game whenever two players
    are accepted.
    """
    def on_start(self):
        self.teams = []
        self.team_names = []

        self.remote_viewers = []
        self.game_master = None

        self._auto_shutdown = False
        self.dump_file = None

    @expose
    def auto_shutdown(self):
        self.ref.reply(self._auto_shutdown)

    @expose
    def set_auto_shutdown(self, value):
        self._auto_shutdown = value

    @expose
    def set_dump_file(self, dump_file):
        self.dump_file = dump_file

    @expose
    def initialize_game(self, layout, number_bots, game_time):
        """ Initialises a new game.
        """
        self.game_master = GameMaster(layout, number_bots, game_time)
        self.check_for_start()

    def _remove_dead_teams(self):
        # check, if previously added teams are still connected:
        zipped = [(team, name) for team, name in zip(self.teams, self.team_names)
                               if not getattr(team, "is_connected", None) or
                               team.is_connected()]

        if zipped:
            teams, team_names = zip(*zipped)
            self.teams = list(teams)
            self.team_names = list(team_names)

    @expose
    def hello(self, team_name, actor_uuid):
        """ Register the actor with address `actor_uuid` as team `team_name`.
        """
        _logger.info("Received 'hello' from '%s'." % team_name)

        if self.ref.remote:
            other_ref = self.ref.remote.create_proxy(actor_uuid)
        else:
            other_ref = actor_registry.get_by_uuid(actor_uuid)

        self.teams.append(other_ref)
        self.team_names.append(team_name)
        self.ref.reply("ok")

        self.check_for_start()

    @expose
    def register_viewer_actor(self, viewer_uuid):
        if self.ref.remote:
            other_ref = self.ref.remote.create_proxy(viewer_uuid)
        else:
            other_ref = actor_registry.get_by_uuid(viewer_uuid)

        viewer = RemoteViewer(other_ref)
        self.remote_viewers.append(viewer)
        self.register_viewer(viewer)
        self.ref.reply("ok")

    @expose
    def register_viewer(self, viewer):
        self.game_master.register_viewer(viewer)

    @expose
    def start_game(self):
        """ Tells the game master to start a new game.

        This method only returns when the game master itself
        returns.
        """
        for team_idx in range(len(self.teams)):
            team_ref = self.teams[team_idx]
            team_name = self.team_names[team_idx]

            remote_player = RemoteTeamPlayer(team_ref)

            self.game_master.register_team(remote_player, team_name=team_name)

        if self.dump_file:
            with open(self.dump_file, 'w') as f:
                viewer = DumpingViewer(f)
                self.game_master.register_viewer(viewer)

                self.game_master.play()
        else:
            self.game_master.play()

        if self._auto_shutdown:
            self.ref.stop()

    def check_for_start(self):
        """ Checks, if a game can be run and start it. """
        if self.game_master is not None and len(self.teams) == 2:
            _logger.info("Two players are available. Starting a game.")
            self.ref.notify("delayed_start_game")

    @expose
    def delayed_start_game(self):
        """ Waits a bit before really starting the game. """
        time.sleep(0.3)
        self.ref.notify("start_game")
