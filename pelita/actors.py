# -*- coding: utf-8 -*-

""" Actor classes which allow for transparent communication
between GameMaster and client Teams over the network.
"""

import sys
import Queue

from pelita.messaging import DispatchingActor, expose, actor_registry, actor_of, RemoteConnection, DeadConnection, ActorNotRunning

from pelita.game_master import GameMaster, PlayerTimeout, PlayerDisconnected

import logging

__docformat__ = "restructuredtext"

_logger = logging.getLogger("pelita")
_logger.setLevel(logging.DEBUG)

TIMEOUT = 3

class _ClientActor(DispatchingActor):
    """ Actor used to communicate with the Server.
    """
    def on_start(self):
        self.team = None
        self.server_actor = None

    @expose
    def register_team(self, team):
        """ We register the team.
        """
        # TODO: Maybe throw an exception, if a team
        # is already registered.
        # Also: investigate how to deal with concurrency issues
        self.team = team

    @expose
    def say_hello(self, main_actor, team_name, host=None, port=None):
        """ Opens a connection to the remote main_actor,
        and sends it a "hello" message with the given team_name.
        """

        try:
            if port is None:
                # assume local game (TODO: put somewhere else?)
                self.server_actor = actor_registry.get_by_name(main_actor)
            else:
                self.server_actor = RemoteConnection().actor_for(main_actor, host, port)
        except DeadConnection:
            # no connection could be established
            self.ref.reply("failed")

        if not self.server_actor:
            _logger.warning("Actor %r not found." % main_actor)
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

    def register_team(self, team):
        """ Registers a team with our local actor.

        Parameters
        ----------
        team : PlayerTeam
            The PlayerTeam which handles all get_move requests.
        """
        self.actor_ref.notify("register_team", [team])

    def connect_local(self, main_actor):
        """ Tells our local actor to establish a local connection
        with other local actor `main_actor`.
        """
        return self.connect(main_actor, None, None)

    def connect(self, main_actor, host="", port=50007):
        """ Tells our local actor to establish a connection with `main_actor`.
        """
        if port is None:
            print "Trying to establish a connection with local actor '%s'..." % main_actor,
        else:
            print "Trying to establish a connection with remote actor '%s'..." % main_actor,
        sys.stdout.flush()

        try:
            res = self.actor_ref.query("say_hello", [main_actor, self.team_name, host, port]).get(TIMEOUT)
            print res
            if res == "ok":
                return True
        except Queue.Empty:
            print "failed due to timeout in actor."
        return False


class RemoteTeamPlayer(object):
    """ This class is registered with the GameMaster and
    relays all get_move requests to the given ActorReference.
    This can be a local or a remote actor.

    It also does some basic checks for correct return values.

    Paramters
    ---------
    reference : ActorReference
        A reference to the local or remote actor.
    """
    def __init__(self, reference):
        self.ref = reference

    def _set_bot_ids(self, bot_ids):
        return self.ref.query("set_bot_ids", bot_ids).get(TIMEOUT)

    def _set_initial(self, universe):
        return self.ref.query("set_initial", [universe]).get(TIMEOUT)

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
        except DeadConnection:
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
        self.game_master = None

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

        self._remove_dead_teams()

        if self.ref.remote:
            other_ref = self.ref.remote.create_proxy(actor_uuid)
        else:
            other_ref = actor_registry.get_by_uuid(actor_uuid)

        self.teams.append(other_ref)
        self.team_names.append(team_name)
        self.ref.reply("ok")

        self.check_for_start()

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

        self.game_master.play()

    def check_for_start(self):
        """ Checks, if a game can be run and start it. """
        if self.game_master is not None and len(self.teams) == 2:
            _logger.info("Two players are available. Starting a game.")

            self.ref.notify("start_game")

