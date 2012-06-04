# -*- coding: utf-8 -*-

""" simplesetup.py defines the SimpleServer and SimpleClient classes
which allow for easy game setup via zmq sockets.

Notes / TODO

Timeout handling was far more elegant (imho) with actors / futures.
Back then, timeouts were reply-based which meant that no other incoming
messages would change the timeouts of other messages.

Now it is all sockets so that each incoming message will reset the timeout
and we need to manually handle this.

A proper solution would use quick-and-dirty queues with size one.
(Which would also allow us to store the received messages.)

In 2.7, thread queues are too slow for that. (Asymptotically they only
check every 50ms for new messages which accumulates quickly in our scheme.)

Gevent queues are fast but do not like zeromq (there is a hack, though);
in a future version we might want to revisit this decision. At the time
we switch to Python 3.2+, if thread queues might have become fast enough
(or maybe if the gevent interface likes our messaging layer), we should
re-investigate this decision.
"""

import time
import logging
import multiprocessing
import threading
import sys

import uuid
import zmq

from .messaging import DeadConnection
from .messaging.json_convert import json_converter
from .layout import get_random_layout, get_layout_by_name
from .game_master import GameMaster, PlayerTimeout, PlayerDisconnected
from .viewer import AbstractViewer

_logger = logging.getLogger("pelita.simplesetup")

__docformat__ = "restructuredtext"

def bind_socket(socket, address, option_hint=None):
    try:
        socket.bind(address)
    except zmq.core.error.ZMQError as e:
        print >>sys.stderr, 'error binding to address %s: %s' % (address, e)
        if option_hint:
            print >>sys.stderr, 'use %s <address> to specify a different port' %\
                (option_hint,)
        raise

class UnknownMessageId(Exception):
    """ Is raised when a reply arrives with unexpected id.
    """
    pass

class ZMQTimeout(Exception):
    """ Is raised when an ZMQ socket does not answer in time.
    """
    pass

class ZMQConnection(object):
    """ This class is supposed to ease request–reply connections
    through a zmq socket. It does so by attaching a uuid to each
    request. It will only accept a reply if this also includes
    this uuid. All other incoming messages will be discarded.

    Please note the following:
      * This class is not thread-safe!
      * There can only be one request at a time. Only the reply for
        the most recent request (= uuid) will be received. Non-matching
        uuids are discarded.
      * There is no storage of messages.

    Parameters
    ----------
    socket : zmq socket
        The zmq socket of this connection

    Attributes
    ----------
    socket : zmq socket
        The zmq socket of this connection
    pollin : zmq poller
        Poller for incoming connections
    pollout : zmq poller
        Poller for outgoing connections
    last_uuid : uuid
        Uuid which the next incoming message has to match
    """
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
            message_obj = {"__uuid__": msg_uuid, "__action__": action, "__data__": data}
            json_message = json_converter.dumps(message_obj)
            self.socket.send(json_message, flags=zmq.NOBLOCK)
        else:
            raise DeadConnection()
        self.last_uuid = msg_uuid

    def recv(self):
        # return tuple
        # (action, data)
        json_message = self.socket.recv()
        py_obj = json_converter.loads(json_message)
        #print repr(json_msg)
        msg_uuid = py_obj["__uuid__"]

        _logger.debug("<--- %s", msg_uuid)

        if msg_uuid == self.last_uuid:
            self.last_uuid = None
            return py_obj["__return__"]
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
    """ This class is registered server-side with the GameMaster
    and sends all requests to the attached zmq socket (to which
    a client player has connected.)

    It also does some basic checks for correct return values.

    Parameters
    ----------
    socket : zmq socket
        The zmq socket of this connection
    """
    def __init__(self, socket):
        self.zmqconnection = ZMQConnection(socket)

    def team_name(self):
        self.zmqconnection.send("team_name", {})
        return self.zmqconnection.recv()

    def set_initial(self, team_id, universe, game_state):
        self.zmqconnection.send("set_initial", {"team_id": team_id,
                                                "universe": universe,
                                                "game_state": game_state})
        return self.zmqconnection.recv()
        #try:
        #    return self.ref.query("set_initial", [universe]).get(TIMEOUT)
        #except (Queue.Empty, ActorNotRunning, DeadConnection):
        #    pass

    def get_move(self, bot_id, universe, game_state):
        try:
            self.zmqconnection.send("get_move", {"bot_id": bot_id,
                                                 "universe": universe,
                                                 "game_state": game_state})
            reply = self.zmqconnection.recv_timeout(game_state["timeout_length"])
            # make sure it is a dict
            reply = dict(reply)
            # make sure that the move is a tuple
            reply["move"] = tuple(reply.get("move"))
            return reply
        except ZMQTimeout:
            # answer did not arrive in time
            raise PlayerTimeout()
        except TypeError:
            # if we could not convert into a tuple or dict (e.g. bad reply)
            return None
        except DeadConnection:
            # if the remote connection is closed
            raise PlayerDisconnected()

    def _exit(self):
        self.zmqconnection.send("exit", {})

class SimpleServer(object):
    """ Sets up a simple Server with most settings pre-configured.

    Usage
    -----
        server = SimpleServer(layout_file="mymaze.layout", rounds=3000)
        server.run()

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
    teams : int, optional
        The number of Teams used in the layout. Default: 2.
    players : int, optional
        The number of Players/Bots used in the layout. Default: 4.
    rounds : int, optional
        The number of rounds played. Default: 3000.
    bind_addrs : string or tuple, optional
        The address(es) which this server uses for its connections. Default: "tcp://*".
    initial_delay : float
        Delays the start of the game by `initial_delay` seconds.
    seed : int, optional
        The initial seed to be passed to GameMaster.

    Raises
    ------
    ValueError:
        if more than one layout keyword is specified
    IOError:
        if layout_file was given, but file does not exist

    """
    def __init__(self, layout_string=None, layout_name=None, layout_file=None,
                 layout_filter='normal_without_dead_ends',
                 teams=2, players=4, rounds=3000, bind_addrs="tcp://*",
                 initial_delay=0.0, max_timeouts=5, timeout_length=3, seed=None):

        if (layout_string and layout_name or
            layout_string and layout_file or
            layout_name and layout_file or
            layout_string and layout_name and layout_file):
            raise  ValueError("Can only supply one of: 'layout_string'"+\
                              "'layout_name' or 'layout_file'")

        elif layout_string:
            self.layout = layout_string
            self.layout_name = ""
        elif layout_name:
            self.layout = get_layout_by_name(layout_name)
            self.layout_name = layout_name
        elif layout_file:
            with open(layout_file) as file:
                self.layout = file.read()
                self.layout_name = file.name
        else:
            self.layout_name, self.layout = get_random_layout(filter=layout_filter)

        self.players = players
        self.number_of_teams = teams
        self.rounds = rounds

        self.game_master = GameMaster(self.layout, self.players, self.rounds,
                                      initial_delay=initial_delay,
                                      max_timeouts=max_timeouts,
                                      timeout_length=timeout_length,
                                      layout_name=self.layout_name,
                                      seed=seed)

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

    def register_teams(self):
        # At this point the clients should have been started as well.
        for team in self.team_players:
            team_name = team.team_name()
            self.game_master.register_team(team, team_name)

    def exit_teams(self):
        for team_player in self.team_players:
            team_player._exit()

    def shutdown(self):
        """ Closes the sockets.

        To be used with care.
        """
        for socket in self.sockets:
            socket.close()

    def run(self):
        self.register_teams()

        self.game_master.play()

        self.exit_teams()

class ExitLoop(Exception):
    """ If this is raised, we’ll close the inner loop.
    """

class SimpleController(object):
    """ Sets up a simple Controller to interact with GameMaster. """

    def __init__(self, game_master, address):
        self.game_master = game_master
        self.address = address

    def on_start(self):
        # We connect here because zmq likes to have its own
        # thread/process/whatever.
        self.context = zmq.Context()
        # We currently use a DEALER which we bind.
        # This means, other DEALERs can connect and
        # each one can take over the control.
        # However, we cannot send any information back to them.
        # (Only one DEALER will receive the data.)
        self.socket = self.context.socket(zmq.DEALER)
        bind_socket(self.socket, self.address, '--controller')

    def run(self):
        self.on_start()
        try:
            while True:
                self._loop()
        except (KeyboardInterrupt, ExitLoop):
            pass

    def _loop(self):
        py_obj = self.socket.recv_json()
        uuid_ = py_obj.get("__uuid__")
        action = py_obj["__action__"]
        data = py_obj.get("__data__") or {}

        # feed client actor here …
        retval = getattr(self, action)(**data)

        if uuid_:
            message_obj = {"__uuid__": uuid_, "__return__": retval}
            json_message = json_converter.dumps(message_obj)
            self.socket.send(json_message)

    def set_initial(self, *args, **kwargs):
        return self.game_master.set_initial(*args, **kwargs)

    def play(self, *args, **kwargs):
        return self.game_master.play(*args, **kwargs)

    def play_round(self, *args, **kwargs):
        return self.game_master.play_round(*args, **kwargs)

    def play_step(self, *args, **kwargs):
        return self.game_master.play_step(*args, **kwargs)

    def update_viewers(self, *args, **kwargs):
        return self.game_master.update_viewers(*args, **kwargs)

    def exit(self):
        raise ExitLoop()

    def __repr__(self):
        return "SimpleController(%r, %r)" % (self.game_master, self.address)


class SimpleClient(object):
    """ Sets up a simple Client with most settings pre-configured.

    Usage
    -----
        client = SimpleClient(SimpleTeam("the good ones", BFSPlayer(), NQRandomPlayer()))
        client.run() # runs in the same thread / process

        client.autoplay_process() # runs in a background process

    Parameters
    ----------
    team: PlayerTeam
        A Player which defines the algorithms for each Bot.
    team_name : string
        The name of the team. (optional, if not defined in team)
    address : string
        The address which the client has to connect to.
    """
    def __init__(self, team, team_name="", address=None):
        self.team = team
        self.team.remote_game = True
        self._team_name = getattr(self.team, "team_name", team_name)

        self.address = address

    def on_start(self):
        # We connect here because zmq likes to have its own
        # thread/process/whatever.
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PAIR)
        self.socket.connect(self.address)

    def run(self):
        self.on_start()
        try:
            while True:
                self._loop()
        except (KeyboardInterrupt, ExitLoop):
            pass

    def _loop(self):
        """ Waits for incoming requests and tries to get a proper
        answer from the player.
        """
        json_message = self.socket.recv()
        py_obj = json_converter.loads(json_message)
        uuid_ = py_obj["__uuid__"]
        action = py_obj["__action__"]
        data = py_obj["__data__"]

        # feed client actor here …
        #
        # TODO: This code is dangerous as a malicious message
        # could call anything on this object. This needs to
        # be fixed analogous to the `expose` method in
        # the messaging framework.
        retval = getattr(self, action)(**data)

        message_obj = {"__uuid__": uuid_, "__return__": retval}
        json_message = json_converter.dumps(message_obj)
        self.socket.send(json_message)

    def set_initial(self, *args, **kwargs):
        return self.team.set_initial(*args, **kwargs)

    def get_move(self, *args, **kwargs):
        return self.team.get_move(*args, **kwargs)

    def exit(self):
        raise ExitLoop()

    def team_name(self):
        return self._team_name

    def autoplay_process(self):
        # We use a multiprocessing because it behaves well with KeyboardInterrupt.
        background_process = multiprocessing.Process(target=self.run)
        background_process.start()
        return background_process

    def autoplay_thread(self):
        # Threading has problems with KeyboardInterrupts but makes it easier
        # (though not simpler) to share state.
        background_thread = threading.Thread(target=self.run)
        background_thread.start()
        return background_thread

    def __repr__(self):
        return "SimpleClient(%r, %r, %r)" % (self.team, self.team_name, self.address)

class SimplePublisher(AbstractViewer):
    """ Sets up a simple Publisher which sends all viewed events
    over a zmq connection.

    Parameters
    ----------
    address : string
        The address which the publisher binds.
    """
    def __init__(self, address):
        self.address = address
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PUB)
        bind_socket(self.socket, self.address, '--publish')

    def set_initial(self, universe):
        message = {"__action__": "set_initial",
                   "__data__": {"universe": universe}}
        as_json = json_converter.dumps(message)
        self.socket.send(as_json)

    def observe(self, universe, game_state):
        message = {"__action__": "observe",
                   "__data__": {"universe": universe,
                                "game_state": game_state}}
        as_json = json_converter.dumps(message)
        self.socket.send(as_json)

class SimpleSubscriber(AbstractViewer):
    """ Subscribes to a given zmq socket and passes
    all incoming data to a viewer.

    Parameters
    ----------
    viewer : Viewer
        Viewer with AbstractPlayer-like interface
    address : string
        The address of the publisher we want to subscribe to.
    """
    def __init__(self, viewer, address):
        self.viewer = viewer
        self.address = address

    def on_start(self):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.setsockopt(zmq.SUBSCRIBE, "")
        self.socket.connect(self.address)

    def run(self):
        self.on_start()
        try:
            while True:
                self._loop()
        except (KeyboardInterrupt, ExitLoop):
            self.socket.close()

    def _loop(self):
        """ Waits for incoming requests and tries to get a proper
        answer from the player.
        """
        data = self.socket.recv()
        py_obj = json_converter.loads(data)

        action = py_obj.get("__action__")
        data = py_obj.get("__data__") or {}

        getattr(self, action)(**data)

    def set_initial(self, universe):
        return self.viewer.set_initial(universe)

    def observe(self, universe, game_state):
        return self.viewer.observe(universe, game_state)

    def exit(self):
        raise ExitLoop()

    def autoplay_process(self):
        # We use a multiprocessing because it behaves well with KeyboardInterrupt.
        background_process = multiprocessing.Process(target=self.run)
        background_process.start()
        return background_process

    def autoplay_thread(self):
        # Threading has problems with KeyboardInterrupts but makes it easier
        # (though not simpler) to share state.
        background_thread = threading.Thread(target=self.run)
        background_thread.start()
        return background_thread

    def __repr__(self):
        return "SimpleSubscriber(%r, %r)" % (self.viewer, self.address)
