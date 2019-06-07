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

_logger = logging.getLogger(__name__)

class ZMQUnreachablePeer(Exception):
    """ Raised when ZMQ cannot send a message (connection may have been lost). """

class ZMQReplyTimeout(Exception):
    """ Is raised when an ZMQ socket does not answer in time. """

class ZMQConnectionError(Exception):
    """ Raised when the connection has errored. """

class UnknownMessageId(Exception):
    """ Is raised when a reply arrives with unexpected id. """

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

def json_default_handler(o):
    """ Pythons built-in json handler has problems converting numpy.in64
    to json. By adding this method as a default= to json.dumps, we can
    tell Python what to do.
    """
    try:
        import numpy as np
        if isinstance(o, np.integer):
            return int(o)
    except ImportError:
        pass
    # we don’t know the type: raise a Type error
    raise TypeError("Cannot convert %r of type %s to json" % (o, type(o)))

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

        # Check before sending that the socket can receive
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
                raise ZMQUnreachablePeer()
        else:
            raise ZMQUnreachablePeer()
        self.last_uuid = msg_uuid

    def recv(self):
        # return tuple
        # (action, data)
        json_message = self.socket.recv_unicode()
        try:
            py_obj = json.loads(json_message)
        except ValueError:
            _logger.warning('Received non-json message from self. Triggering a timeout.')
            raise ZMQReplyTimeout()
        #print repr(json_msg)

        try:
            msg_error = py_obj['__error__']
            error_type, error_message = msg_error
            _logger.warning(f'Received error reply ({error_type}): {error_message}. Closing socket.')
            self.socket.close()
            raise ZMQConnectionError(*msg_error)
        except KeyError:
            pass

        try:
            msg_uuid = py_obj["__uuid__"]
        except KeyError:
            _logger.warning('__uuid__ missing in message.')
            msg_uuid = None
        
        msg_return = py_obj.get("__return__")

        _logger.debug("<--- %r [%s]", msg_return, msg_uuid)

        if msg_uuid == self.last_uuid:
            self.last_uuid = None
            return msg_return
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
                raise ZMQReplyTimeout()
        raise ZMQReplyTimeout()

    def __repr__(self):
        return "ZMQConnection(%r)" % self.socket

class ExitLoop(Exception):
    """ If this is raised, we’ll close the inner loop.
    """


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
                json_message = json.dumps(message_obj, default=json_default_handler)
                self.socket.send_unicode(json_message)
            except NameError:
                pass

    def set_initial(self, team_id, game_state):
        return self.team.set_initial(team_id, game_state)

    def get_move(self, game_state):
        return self.team.get_move(game_state)

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

class SimplePublisher:
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
        _logger.debug("--#>")
        as_json = json.dumps(message)
        self.socket.send_unicode(as_json)

    def set_initial(self, game_state):
        message = {"__action__": "set_initial",
                   "__data__": {"game_state": game_state}}
        self._send(message)

    def observe(self, game_state):
        message = {"__action__": "observe",
                   "__data__": {"game_state": game_state}}
        self._send(message)

    def show_state(self, game_state):
        message = {"__action__": "observe",
                   "__data__": game_state}
        self._send(message)

