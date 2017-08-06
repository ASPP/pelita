""" simplesetup.py defines the SimpleServer and SimpleClient classes
which allow for easy game setup via zmq sockets.

Notes
-----

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
(or maybe if the gevent interface likes our old messaging layer), we should
re-investigate this decision.
"""

import json
import logging
import multiprocessing
import re
import sys
import time
import uuid

import zmq

from .datamodel import CTFUniverse
from .game_master import GameMaster, PlayerDisconnected, PlayerTimeout
from .viewer import AbstractViewer

_logger = logging.getLogger("pelita.simplesetup")

class DeadConnection(Exception):
    """ Raised when the connection has been lost. """

#: The timeout to use during sending
DEAD_CONNECTION_TIMEOUT = 3.0

def extract_port_range(address):
    """ We additionally allow for setting a port range in rectangular brackets:
        tcp://127.0.0.1:[50100:50120]
    """
    range_pattern = re.compile(r"(?P<addr>.*?):\[(?P<port_min>\d+):(?P<port_max>\d+)\]")
    random_pattern = re.compile(r"(?P<addr>.*?):\*")
    port_pattern = re.compile(r"(?P<addr>.*?):(?P<port>\d+)")

    m = range_pattern.match(address)
    if m:
        return {"addr": m.group(1), "port_min": int(m.group(2)), "port_max": int(m.group(3))}
    m = random_pattern.match(address)
    if m:
        return {"addr": m.group(1), "port_min": None, "port_max": None}
    m = port_pattern.match(address)
    if m:
        return {"addr": address}
    return {"addr": address}

def bind_socket(socket, address, option_hint=None):
    try:
        address_range = extract_port_range(address)
        addr = address_range["addr"]
        try:
            port_min = address_range["port_min"]
            port_max = address_range["port_max"]
            if port_min and port_max:
                port = socket.bind_to_random_port(addr, port_min, port_max)
            else:
                port = socket.bind_to_random_port(addr)
            bind_addr = "{0}:{1}".format(addr, port)
            return bind_addr

        except KeyError:
            socket.bind(addr)
            return addr

    except (zmq.ZMQError, zmq.ZMQBindError) as e:
        print('error binding to address %s: %s' % (address, e), file=sys.stderr)
        if option_hint:
            print('use %s <address> to specify a different port' %\
                (option_hint,), file=sys.stderr)
        raise

class UnknownMessageId(Exception):
    """ Is raised when a reply arrives with unexpected id.
    """
    pass

class ZMQTimeout(Exception):
    """ Is raised when an ZMQ socket does not answer in time.
    """
    pass

class ZMQConnection:
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

    def send(self, action, data, timeout=None):
        if timeout is None:
            timeout = DEAD_CONNECTION_TIMEOUT

        msg_uuid = str(uuid.uuid4())
        _logger.debug("---> %r [%s]", action, msg_uuid)

        # Check before sending. Forever is a long time.
        socks = dict(self.pollout.poll(timeout * 1000))
        if socks.get(self.socket) == zmq.POLLOUT:
            # I think we need to set NOBLOCK here, else we may run into a
            # race condition if a connection was closed between poll and send.
            # NOBLOCK should raise, so we can catch that
            message_obj = {"__uuid__": msg_uuid, "__action__": action, "__data__": data}
            json_message = json.dumps(message_obj)
            try:
                self.socket.send_unicode(json_message, flags=zmq.NOBLOCK)
            except zmq.ZMQError as e:
                _logger.info("Could not send message. Assume socket is unavailable. %r", e)
                raise DeadConnection()
        else:
            raise DeadConnection()
        self.last_uuid = msg_uuid

    def recv(self):
        # return tuple
        # (action, data)
        json_message = self.socket.recv_unicode()
        py_obj = json.loads(json_message)
        #print repr(json_msg)
        msg_uuid = py_obj["__uuid__"]
        msg_action = py_obj.get("__action__") or py_obj.get("__return__")

        _logger.debug("<--- %r [%s]", msg_action, msg_uuid)

        if msg_uuid == self.last_uuid:
            self.last_uuid = None
            return py_obj["__return__"]
        else:
            self.last_uuid = None
            raise UnknownMessageId()

    def recv_timeout(self, timeout):
        if timeout is None:
            return self.recv()

        time_now = time.monotonic()
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
                    time_now = time.monotonic()
                    continue
                # answer did not arrive in time
            else:
                raise ZMQTimeout()
        raise ZMQTimeout()

    def __repr__(self):
        return "ZMQConnection(%r)" % self.socket


class RemoteTeamPlayer:
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
        try:
            self.zmqconnection.send("team_name", {})
            return self.zmqconnection.recv_timeout(DEAD_CONNECTION_TIMEOUT)
        except ZMQTimeout:
            _logger.info("Detected a timeout, returning a string nonetheless.")
            return "%error%"
        except DeadConnection:
            _logger.info("Detected a DeadConnection, returning a string nonetheless.")
            return "%error%"

    def set_initial(self, team_id, universe, game_state):
        try:
            self.zmqconnection.send("set_initial", {"team_id": team_id,
                                                    "universe": universe._to_json_dict(),
                                                    "game_state": game_state})
            return self.zmqconnection.recv_timeout(game_state["timeout_length"])
        except ZMQTimeout:
            # answer did not arrive in time
            raise PlayerTimeout()
        except DeadConnection:
            _logger.info("Detected a DeadConnection.")

    def get_move(self, bot_id, universe, game_state):
        try:
            self.zmqconnection.send("get_move", {"bot_id": bot_id,
                                                 "universe": universe._to_json_dict(),
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
        try:
            self.zmqconnection.send("exit", {}, timeout=1)
        except DeadConnection:
            _logger.info("Remote Player %r is already dead during exit. Ignoring.", self)

    def __repr__(self):
        return "RemoteTeamPlayer(%r)" % self.zmqconnection

class SimpleServer:
    """ Sets up a simple Server with most settings pre-configured.

    Example
    -------
    Initialise as follows::

        server = SimpleServer(layout_string=layout, rounds=3000)
        server.run()

    Parameters
    ----------
    layout_string : string
        initial layout as string
    teams : int, optional
        The number of Teams used in the layout. Default: 2.
    players : int, optional
        The number of Players/Bots used in the layout. Default: 4.
    rounds : int, optional
        The number of rounds played. Default: 3000.
    bind_addrs : list of strings, optional
        The address(es) which this server uses for its connections.
        Defaults to ["tcp://*"] * teams, if not given.
    initial_delay : float
        Delays the start of the game by `initial_delay` seconds.
    layout_name : string, optional
        The name of the given layout string.
    seed : int, optional
        The initial seed to be passed to GameMaster.

    Raises
    ------
    ValueError:
        if more than one layout keyword is specified
    IOError:
        if layout_file was given, but file does not exist

    """
    def __init__(self, layout_string, teams=2, players=4, rounds=3000, bind_addrs=None,
                 initial_delay=0.0, max_timeouts=5, timeout_length=3, layout_name=None,
                 seed=None):

        self.players = players
        self.number_of_teams = teams
        self.rounds = rounds

        if bind_addrs is None:
            bind_addrs = ["tcp://*"] * self.number_of_teams

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

            bind_to_random = False
            if address.startswith("tcp://"):
                split_address = address.split("tcp://")
                if not ":" in split_address[1]:
                    # assume no port has been given:
                    bind_to_random = True

            try:
                if bind_to_random:
                    socket_port = socket.bind_to_random_port(address)
                    address = address + (":%d" % socket_port)
                else:
                    socket.bind(address)
                _logger.info("Bound zmq.PAIR to %s", address)
            except zmq.ZMQError:
                print("ZMQError while trying to bind {}".format(address))
                raise

            self.sockets.append(socket)
            self.bind_addresses.append(address)

            team_player = RemoteTeamPlayer(socket)
            self.team_players.append(team_player)

        self.game_master = GameMaster(layout_string, self.team_players,
                                      self.players, self.rounds,
                                      initial_delay=initial_delay,
                                      max_timeouts=max_timeouts,
                                      timeout_length=timeout_length,
                                      layout_name=layout_name,
                                      seed=seed)

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
        self.game_master.play()

        self.exit_teams()

class ExitLoop(Exception):
    """ If this is raised, we’ll close the inner loop.
    """

class SimpleController:
    """ Sets up a simple Controller to interact with GameMaster. """

    def __init__(self, game_master, address, reply_to=None):
        self.game_master = game_master
        self.address = address

        self.context = zmq.Context()
        # We currently use a ROUTER which we bind.
        # This means, other DEALERs can connect and
        # each one can take over the control.
        self.socket = self.context.socket(zmq.ROUTER)
        self.socket_addr = bind_socket(self.socket, self.address, '--controller')
        _logger.debug("Bound zmq.ROUTER to {}".format(self.socket_addr))

    def run(self):
        try:
            while True:
                self._loop()
        except (KeyboardInterrupt, ExitLoop):
            pass

    def _loop(self):
        addr, py_obj_raw = self.socket.recv_multipart()
        py_obj = json.loads(py_obj_raw.decode('utf-8'))
        uuid_ = py_obj.get("__uuid__")
        action = py_obj["__action__"]
        data = py_obj.get("__data__") or {}

        # feed client actor here …
        retval = getattr(self, action)(**data)

        if uuid_:
            message_obj = {"__uuid__": uuid_, "__return__": retval}
            json_message = json.dumps(message_obj)
            self.socket.send_multipart([addr, json_message.encode()])

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


class SimpleClient:
    """ Sets up a simple Client with most settings pre-configured.

    Example
    -------
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
        try:
            self.socket.connect(self.address)
        except zmq.ZMQError as e:
            raise IOError('failed to connect the client to address %s: %s'
                          % (self.address, e))

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
        json_message = self.socket.recv_unicode()
        py_obj = json.loads(json_message)
        uuid_ = py_obj["__uuid__"]
        action = py_obj["__action__"]
        data = py_obj["__data__"]

        try:
            # feed client actor here …
            #
            # TODO: This code is dangerous as a malicious message
            # could call anything on this object. This needs to
            # be fixed analogous to the `expose` method in
            # the previous messaging framework.
            retval = getattr(self, action)(**data)
        except (KeyboardInterrupt, ExitLoop):
            raise
        except Exception as e:
            msg = "Exception in client code for team %s." % self.team
            print(msg, file=sys.stderr)
            # return None. Let it crash next time the server tries to send.
            retval = None
            raise
        finally:
            try:
                message_obj = {"__uuid__": uuid_, "__return__": retval}
                json_message = json.dumps(message_obj)
                self.socket.send_unicode(json_message)
            except NameError:
                pass

    def set_initial(self, team_id, universe, game_state):
        return self.team.set_initial(team_id, CTFUniverse._from_json_dict(universe), game_state)

    def get_move(self, bot_id, universe, game_state):
        return self.team.get_move(bot_id, CTFUniverse._from_json_dict(universe), game_state)

    def exit(self):
        raise ExitLoop()

    def team_name(self):
        return self._team_name

    def autoplay_process(self):
        # We use a multiprocessing because it behaves well with KeyboardInterrupt.
        background_process = multiprocessing.Process(target=self.run)
        background_process.start()
        return background_process

    def __repr__(self):
        return "SimpleClient(%r, %r, %r)" % (self.team, self.team_name(), self.address)

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
        self.socket_addr = bind_socket(self.socket, self.address, '--publish')
        _logger.debug("Bound zmq.PUB to {}".format(self.socket_addr))


    def _send(self, message):
        as_json = json.dumps(message)
        self.socket.send_unicode(as_json)

    def set_initial(self, universe):
        message = {"__action__": "set_initial",
                   "__data__": {"universe": universe._to_json_dict()}}
        self._send(message)

    def observe(self, universe, game_state):
        message = {"__action__": "observe",
                   "__data__": {"universe": universe._to_json_dict(),
                                "game_state": game_state}}
        self._send(message)

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
        self.socket.setsockopt_unicode(zmq.SUBSCRIBE, "")
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
        data = self.socket.recv_unicode()
        py_obj = json.loads(data)

        action = py_obj.get("__action__")
        data = py_obj.get("__data__") or {}

        getattr(self, action)(**data)

    def set_initial(self, universe):
        return self.viewer.set_initial(CTFUniverse._from_json_dict(universe))

    def observe(self, universe, game_state):
        return self.viewer.observe(CTFUniverse._from_json_dict(universe), game_state)

    def exit(self):
        raise ExitLoop()

    def autoplay_process(self):
        # We use a multiprocessing because it behaves well with KeyboardInterrupt.
        background_process = multiprocessing.Process(target=self.run)
        background_process.start()
        return background_process

    def __repr__(self):
        return "SimpleSubscriber(%r, %r)" % (self.viewer, self.address)
