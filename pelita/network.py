
import json
import logging
import sys
import time
from urllib.parse import urlparse
import uuid

import zmq

_logger = logging.getLogger(__name__)

# 41736 is the word PELI(T)A when read upside down in reverse without glasses
# The missing T stands for tcp
PELITA_PORT = 41736

## Pelita network data structures

# ControlRequest
# {__action__}

# ViewerUpdate
# {__action__, __data__}

# Request
# {__uuid__, __action__, __data__}

# Reply
# {__uuid__, __return__}

# Error
# {__uuid__, __error__, __error_msg__}


class ZMQUnreachablePeer(Exception):
    """ Raised when ZMQ cannot send a message (connection may have been lost). """


class ZMQReplyTimeout(Exception):
    """ Is raised when an ZMQ socket does not answer in time. """


class ZMQClientError(Exception):
    """ Used to propagate errors from the client.
    Raised when the zmq connection receives an __error__ message. """
    def __init__(self, message, error_type, *args):
        self.message = message
        self.error_type = error_type
        super().__init__(message, error_type, *args)


#: The timeout to use during sending
DEAD_CONNECTION_TIMEOUT = 3.0


def bind_socket(socket: zmq.Socket, address, option_hint=None):
    parsed_address = urlparse(address)

    # NB: We cannot use parsed_address.geturl() to generate a nice url for zmq
    # as this will eat the empty hostname in a file path and zmq does not like that.
    # file:///tmp/a -> file:/tmp/a

    try:
        if parsed_address.scheme == 'tcp' and parsed_address.port is None:
            port = socket.bind_to_random_port(address)
            return f'tcp://{parsed_address.hostname}:{port}'
        else:
            socket.bind(address)
            return address

    except (zmq.ZMQError, zmq.ZMQBindError) as e:
        print('error binding to address %s: %s' % (address, e), file=sys.stderr)
        if option_hint:
            print('use %s <address> to specify a different port' %\
                (option_hint,), file=sys.stderr)
        raise


class SetEncoder(json.JSONEncoder):
   def default(self, obj):
      if isinstance(obj, set):
         return list(obj)
      return json.JSONEncoder.default(self, obj)


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
    """
    def __init__(self, socket):
        self.socket = socket

        self.socket.setsockopt(zmq.LINGER, 0)
        self.socket.setsockopt(zmq.AFFINITY, 1)
        #self.setsockopt(zmq.RCVTIMEO, 2000)

        self.pollin = zmq.Poller()
        self.pollin.register(socket, zmq.POLLIN)
        self.pollout = zmq.Poller()
        self.pollout.register(socket, zmq.POLLOUT)

    def send(self, action, data, timeout=None):
        """ Sends a message or request `action`
        and attached data to the socket and returns the
        message id that is needed to receive the reply.
        """

        if timeout is None:
            timeout = DEAD_CONNECTION_TIMEOUT

        msg_id = str(uuid.uuid4())
        _logger.debug("---> %r [%s]", action, msg_id)

        # Check before sending that the socket can receive
        socks = dict(self.pollout.poll(timeout * 1000))
        if socks.get(self.socket) == zmq.POLLOUT:
            # I think we need to set NOBLOCK here, else we may run into a
            # race condition if a connection was closed between poll and send.
            # NOBLOCK should raise, so we can catch that
            message_obj = {"__uuid__": msg_id, "__action__": action, "__data__": data}
            json_message = json.dumps(message_obj, cls=SetEncoder)
            try:
                self.socket.send_unicode(json_message, flags=zmq.NOBLOCK)
            except zmq.ZMQError as e:
                _logger.info("Could not send message. Assume socket is unavailable. %r", e)
                raise ZMQUnreachablePeer()
        else:
            raise ZMQUnreachablePeer()
        return msg_id

    def _recv(self):
        """ Receive the next message on the socket.

        Returns
        -------
        (msg_id, reply)
            The message id and its data.

        Raises
        ------
        ZMQReplyTimeout
            if the message cannot be parsed from JSON
        ZMQClientError
            if an error message is returned
        """
        json_message = self.socket.recv_unicode()
        try:
            py_obj = json.loads(json_message)
        except ValueError:
            _logger.warning('Received non-json message from self. Triggering a timeout.')
            raise ZMQReplyTimeout()

        try:
            error_type = py_obj['__error__']
            error_message = py_obj.get('__error_msg__', '')
            _logger.warning(f'Received error reply ({error_type}): {error_message}. Closing socket.')
            self.socket.close()
            raise ZMQClientError(error_message, error_type)
        except KeyError:
            pass

        try:
            msg_id = py_obj["__uuid__"]
        except KeyError:
            msg_id = None
            _logger.warning('__uuid__ missing in message.')

        msg_return = py_obj.get("__return__")

        _logger.debug("<--- %r [%s]", msg_return, msg_id)
        return msg_id, msg_return

    def recv_timeout(self, expected_id, timeout):
        """ Waits `timeout` seconds for a reply with msg_id `expected_id`.

        Returns
        -------
        reply
            The reply for the `expected_id`

        Raises
        ------
        ZMQReplyTimeout
            if the message cannot be parsed from JSON
            if the message was not received in time
        ZMQConnectionError
            if an error message is returned
        """
        # special case for no timeout
        # just loop until we receive the correct reply
        if timeout is None:
            while True:
                msg_id, reply = self._recv()
                if msg_id == expected_id:
                    return reply

        # normal timeout handling

        time_now = time.monotonic()
        # calculate until when it may take
        # NB: When rewriting this code,
        # ensure that the case timeout=0
        # can still be handled
        timeout_until = time_now + timeout

        while time_now < timeout_until:
            time_left = timeout_until - time_now

            socks = dict(self.pollin.poll(time_left * 1000)) # poll needs milliseconds
            if socks.get(self.socket) == zmq.POLLIN:
                msg_id, reply = self._recv()

                # check, if it is the correct reply and return
                if msg_id == expected_id:
                    return reply

                else:
                    # We received a message with the wrong id.
                    # Reset the current time and try again.
                    time_now = time.monotonic()
                    continue
            else:
                # poll timed out
                # answer did not arrive in time
                break

        raise ZMQReplyTimeout()

    def __repr__(self):
        return "ZMQConnection(%r)" % self.socket

class ZMQPublisher:
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

    def _send(self, action, data):
        info = {'round': data['round'], 'turn': data['turn']}
        if data['gameover']:
            info['gameover'] = True
        _logger.debug(f"--#> [{action}] %r", info)
        message = {"__action__": action, "__data__": data}
        as_json = json.dumps(message, cls=SetEncoder)
        self.socket.send_unicode(as_json)

    def show_state(self, game_state):
        self._send(action="observe", data=game_state)


class Controller:
    def __init__(self, address='tcp://127.0.0.1', zmq_context=None):
        self.address = address
        if zmq_context:
            self.context = zmq_context
        else:
            self.context = zmq.Context()
        # We use a ROUTER which we bind.
        # This means other DEALERs can connect and
        # each one can take over control.
        self.socket = self.context.socket(zmq.ROUTER)
        self.socket_addr = bind_socket(self.socket, self.address)
        self.pollin = zmq.Poller()
        self.pollin.register(self.socket, zmq.POLLIN)
        _logger.debug("Bound zmq.ROUTER to {}".format(self.socket_addr))

    def await_action(self, await_action, timeout=None, accept_exit=True):
        """ Waits `timeout` seconds to receive an action. """
        t_start = time.monotonic()
        if timeout is None:
            t_end = float("inf")
        else:
            t_end = t_start + timeout

        while time.monotonic() < t_end:

            # TODO: Proper time left handling
            timeoutmillis = timeout * 1000 if timeout is not None else None

            sock = dict(self.pollin.poll(timeoutmillis)) # poll needs milliseconds
            if sock.get(self.socket) == zmq.POLLIN:
                try:
                    sender, msg = self.socket.recv_multipart()
                    msg = json.loads(msg)
                    action = msg['__action__']
                    _logger.debug('<=== %r from %r', action, sender)
                except ValueError:
                    _logger.warning('Could not deserialize message from %r', sender)
                    continue
                except (TypeError, KeyError):
                    _logger.warning('No action in message from %r', sender)
                    continue

                expected_actions = [await_action]
                if accept_exit:
                    expected_actions.append('exit')
                if action in expected_actions:
                    return action
                _logger.warning('Unexpected action %r. (Expected: %s) Ignoring.', action, ", ".join(expected_actions))
                continue


    def recv_start(self, timeout=None):
        """ Waits `timeout` seconds for start message.

        Returns `True`, when the message arrives, `False` when an exit
        message arrives or a timeout occurs.
        """


def setup_controller(zmq_context=None):
    if not zmq_context:
        import zmq
        zmq_context = zmq.Context()
    controller = Controller(zmq_context=zmq_context)
    return controller
