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
import uuid
import zmq

from .messaging import actor_of, RemoteConnection, DeadConnection
from .layout import get_random_layout, get_layout_by_name
from pelita.game_master import GameMaster, PlayerTimeout, PlayerDisconnected
from pelita.messaging.json_convert import json_converter
from pelita.viewer import AbstractViewer

from .viewer import AsciiViewer, AbstractViewer
from .utils.signal_handlers import keyboard_interrupt_handler, exit_handler

_logger = logging.getLogger("pelita.simplesetup")

__docformat__ = "restructuredtext"

TIMEOUT = 3

class UnknownMessageId(Exception):
    pass

class ZMQTimeout(Exception):
    pass

class MiniZMQActor(object): # TODO: This is no actor. This is not even thread-safe!!!
    def __init__(self, socket):
        self.socket = socket
        self.pollin = zmq.Poller()
        self.pollin.register(socket, zmq.POLLIN)
        self.pollout = zmq.Poller()
        self.pollout.register(socket, zmq.POLLOUT)

        self.last_uuid = None

    def send(self, action, data, timeout=3.0):
        msg_uuid = str(uuid.uuid4())
        _logger.debug("---> %s", msg_uuid)

        # Check before sending. Forever is a long time.
        socks = dict(self.pollout.poll(timeout * 1000))
        if socks.get(self.socket) == zmq.POLLOUT:
            # I think we need to set NOBLOCK here, else we may run into a
            # race condition if a connection was closed between poll and send.
            self.socket.send_pyobj({"__uuid__": msg_uuid, "__action__": action, "__data__": data}, flags=zmq.NOBLOCK)
        else:
            raise DeadConnection()
        self.last_uuid = msg_uuid

    def recv(self):
        # return tuple
        # (action, data)
        json_msg = self.socket.recv_pyobj()
        #print repr(json_msg)
        msg_uuid = json_msg["__uuid__"]

        _logger.debug("<--- %s", msg_uuid)

        if msg_uuid == self.last_uuid:
            self.last_uuid = None
            return json_msg["__return__"]
        else:
            self.last_uuid = None
            raise UnknownMessageId()

    def recv_timeout(self, timeout):
        time_now = time.time()
        #: calculate until when it may take
        timeout_until = time_now + timeout

        while time_now < timeout_until:
            time_left = timeout_until - time_now

            socks = dict(self.pollin.poll(time_left * 1000)) # poll needs milliseconds
            if socks.get(self.socket) == zmq.POLLIN:
                try:
                    reply = self.recv()
                    # No error? Then it is the answer that we wanted. Good.
                    return reply
                except UnknownMessageId:
                    # Okay, false alarm. Reset the current time and try again.
                    time_now = time.time()
                    continue
                # answer did not arrive in time
            else:
                raise ZMQTimeout()
        raise ZMQTimeout()


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
    def __init__(self, socket):
        self.zmqactor = MiniZMQActor(socket)

    def _set_bot_ids(self, bot_ids):
        #try:
        self.zmqactor.send("_set_bot_ids", [bot_ids])
        return self.zmqactor.recv()
            #return self.ref.query("set_bot_ids", bot_ids).get(TIMEOUT)
        #except (Queue.Empty, ActorNotRunning, DeadConnection):
        #    pass

    def _set_initial(self, universe):
        self.zmqactor.send("_set_initial", [universe])
        return self.zmqactor.recv()
        #try:
        #    return self.ref.query("set_initial", [universe]).get(TIMEOUT)
        #except (Queue.Empty, ActorNotRunning, DeadConnection):
        #    pass

    def _get_move(self, bot_idx, universe):
        try:
            self.zmqactor.send("_get_move", [bot_idx, universe]) # TODO timeout
            reply = self.zmqactor.recv_timeout(TIMEOUT)
            return reply
        except ZMQTimeout:
            # answer did not arrive in time
            raise PlayerTimeout()
        except TypeError:
            # if we could not convert into a tuple (e.g. bad reply)
            return None
        except DeadConnection:
            # if the remote connection is closed
            raise PlayerDisconnected()

class ZMQServer(object):
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
                 teams=2,
                 players=4, rounds=3000, bind_addrs=None,
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
        self.number_of_teams = teams
        self.rounds = rounds
        self.silent = silent

        self.dump_to_file = dump_to_file

        self.game_master = GameMaster(self.layout, self.players, self.rounds)

        if bind_addrs is None:
            _logger.debug("No address given. Defaulting to 'tcp://*'.")
            bind_addrs = "tcp://*"

        if isinstance(bind_addrs, tuple):
            pass
        elif isinstance(bind_addrs, basestring):
            if not bind_addrs.startswith("tcp://"):
                raise ValueError("non-tcp bind_addrs cannot be shared.")
            bind_addrs = (bind_addrs, ) * self.number_of_teams
        else:
            raise TypeError("bind_addrs must be tuple or string.")

        #: declare the zmq Context for this server thread
        self.context = zmq.Context()

        #: the sockets being used
        self.sockets = []

        #: the bind addresses
        self.bind_addresses = []

        #: the remote team players which are used for sending
        self.team_players = []

        for address in bind_addrs:
            socket = self.context.socket(zmq.PAIR)
            _logger.info("Binding to %s", address)

            bind_to_random = False
            if address.startswith("tcp://"):
                split_address = address.split("tcp://")
                if not ":" in split_address[1]:
                    # assume no port has been given:
                    bind_to_random = True

            if bind_to_random:
                socket_port = socket.bind_to_random_port(address)
                address = address + (":%d" % socket_port)
            else:
                socket.bind(address)

            self.sockets.append(socket)
            self.bind_addresses.append(address)

            team_player = RemoteTeamPlayer(socket)
            self.team_players.append(team_player)

        for team in self.team_players:
            self.game_master.register_team(team)

    def run(self):
        self.game_master.play()

class ZMQClient(object):
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
    def __init__(self, team, team_name="", address=None):
        self.team = team
        self.team_name = getattr(self.team, "team_name", team_name)

        self.address = address

    def loop(self):
        try:
            self._loop()
        except KeyboardInterrupt:
            pass

    def _loop(self):
        """ Creates a new ClientActor, and connects it with
        the Server.
        This method only returns when the ClientActor finishes.
        """

        # We connect here because zmq likes to have its own
        # thread/process/whatever.
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PAIR)
        self.socket.connect(self.address)

        while True:
            py_obj = self.socket.recv_pyobj()
            uuid_ = py_obj["__uuid__"]
            action = py_obj["__action__"]
            data = py_obj["__data__"]

            # feed client actor here …

            retval = getattr(self.team, action)(*data)
            #print action, retval

            self.socket.send_pyobj({"__uuid__": uuid_, "__return__": retval})

    def autoplay_process(self):
        # We use a multiprocessing because it behaves well with KeyboardInterrupt.
        background_process = multiprocessing.Process(target=self.loop)
        background_process.start()
        return background_process

    def autoplay_thread(self):
        # We cannot use multiprocessing in a local game.
        # Or that is, we cannot until we also use multiprocessing Queues.
        background_thread = threading.Thread(target=self.loop)
        background_thread.start()
        return background_thread

class ZMQPublisher(AbstractViewer):
    def __init__(self, address):
        self.address = address
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PUB)
        self.socket.bind(self.address)

    def set_initial(self, universe):
        as_json = json_converter.dumps({"universe": universe})
        self.socket.send(as_json)

    def observe(self, round_, turn, universe, events):
        as_json = json_converter.dumps({
            "round": round_,
            "turn": turn,
            "universe": universe,
            "events": events})
        self.socket.send(as_json)
