
import json
import logging
import sys
import time
import uuid
from urllib.parse import urlparse

import zmq

from .base_utils import default_zmq_context

_logger = logging.getLogger(__name__)

# 41736 is the word PELI(T)A when read upside down in reverse without glasses
# The missing T stands for tcp
PELITA_PORT = 41736


class RemotePlayerSendError(Exception):
    """ Raised when ZMQ cannot send a message (connection may have been lost). """


class RemotePlayerRecvTimeout(Exception):
    """ Is raised when an ZMQ socket does not answer in time. """

class RemotePlayerFailure(Exception):
    """ Used to propagate errors from the client.
    Raised when the zmq connection receives an __error__ message. """
    def __init__(self, error_type, error_msg):
        self.error_type = error_type
        self.error_msg = error_msg
        super().__init__(error_type, error_msg)

    def __str__(self):
        return f"{self.error_type}: {self.error_msg}"

class RemotePlayerProtocolError(RemotePlayerFailure):
    def __init__(self):
        super().__init__("BadProtocol", "Bad protocol error")

class BadState(Exception):
    pass


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


class RemotePlayerConnection:
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

    def __init__(self, socket: zmq.Socket):
        self.socket = socket

        self.socket.setsockopt(zmq.LINGER, 0)
        self.socket.setsockopt(zmq.AFFINITY, 1)
        #self.setsockopt(zmq.RCVTIMEO, 2000)

        self.pollin = zmq.Poller()
        self.pollin.register(socket, zmq.POLLIN)
        self.pollout = zmq.Poller()
        self.pollout.register(socket, zmq.POLLOUT)

        self.state = "WAIT"

    def _send(self, action, data, msg_id):
        """ Sends a message or request `action`
        and attached data to the socket.
        """

        timeout = DEAD_CONNECTION_TIMEOUT

        if msg_id is not None:
            message_obj = {"__uuid__": msg_id, "__action__": action, "__data__": data}
            _logger.debug("?--> %r [%s]", action, msg_id)
        else:
            message_obj = {"__action__": action, "__data__": data}
            _logger.debug("---> %r", action)

        # Check before sending that the socket can receive
        socks = dict(self.pollout.poll(timeout * 1000))
        if self.socket in socks and socks[self.socket] == zmq.POLLOUT:
            # I think we need to set NOBLOCK here, else we may run into a
            # race condition if a connection was closed between poll and send.
            # NOBLOCK should raise, so we can catch that
            json_message = json.dumps(message_obj, cls=SetEncoder)
            try:
                self.socket.send_unicode(json_message, flags=zmq.NOBLOCK)
            except zmq.ZMQError as e:
                _logger.info("Could not send message. Socket is unavailable. %r", e)
                raise RemotePlayerSendError()
        else:
            raise RemotePlayerSendError()
        return msg_id

    def send_req(self, action, data):
        """ Sends a message or request `action`
        and attached data to the socket and returns the
        message id that is needed to receive the reply.
        """
        msg_id = str(uuid.uuid4())
        self._send(action=action, data=data, msg_id=msg_id)
        return msg_id

    def send_exit(self, payload):
        if self.state == "EXITING":
            return

        if self.state == "CLOSED":
            # TODO: For now we simply ignore if the state is CLOSED
            return

        self.state = "EXITING"
        msg_id = self.send_req("exit", payload)
        return msg_id

    def _recv(self):
        """ Receive the next message on the socket. Will wait forever

        Returns
        -------
        (msg_id, reply)
            The message id and its data.

        Raises
        ------
        ZMQReplyTimeout
            if the message cannot be parsed from JSON
        PelitaRemoteError
            if an error message is returned
        """
        json_message = self.socket.recv_unicode()
        try:
            py_obj = json.loads(json_message)
        except ValueError:
            _logger.warning('Received non-json message. Closing socket.')

            # TODO: Should we tell the remote end that we are exiting?
            self.socket.close()
            self.state = "CLOSED"

            raise RemotePlayerProtocolError

        if '__error__' in py_obj:
            error_type = py_obj['__error__']
            error_message = py_obj.get('__error_msg__', '')
            _logger.debug("<--X %r: %s", error_type, error_message)
            _logger.warning(f'Received error reply ({error_type}): {error_message}. Closing socket.')
            self.socket.close()

            self.state = "CLOSED"

            # Failure in the pelita code on client side
            raise RemotePlayerFailure(error_type, error_message)

        if '__uuid__' in py_obj:
            msg_id = py_obj['__uuid__']
            msg_return = py_obj.get("__return__")
            _logger.debug("<--! %r [%s]", msg_return, msg_id)

            return msg_id, msg_return

        if '__status__' in py_obj:
            msg_ack = py_obj['__status__'] # == 'ok'
            msg_data = py_obj.get('__data__')
            _logger.debug("<--o %r %r", msg_ack, msg_data)

            self.state = "CONNECTED"

            return None, msg_data

        _logger.warning('Received malformed json message. Closing socket.')

        # TODO: Should we tell the remote end that we are exiting?
        self.socket.close()
        self.state = "CLOSED"

        raise RemotePlayerProtocolError


    def recv_status(self, timeout):
        """ Receive the next message on the socket.

        Returns
        -------
        status
            The message status

        Raises
        ------
        ZMQReplyTimeout
            if the message cannot be parsed from JSON
        PelitaRemoteError
            if an error message is returned

        """
        if not self.state == "WAIT":
            raise BadState

        status = self.recv_timeout(None, timeout)

        self.state = "CONNECTED"

        return status

    def recv_reply(self, expected_id, timeout):
        match self.state:
            case "CONNECTED"|"EXITING":
                return self.recv_timeout(expected_id, timeout)

        raise BadState(self.state)

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
        if self.state == "CLOSED":
            return

        time_now = time.monotonic()
        # calculate until when it may take
        # NB: When rewriting this code,
        # ensure that the case timeout=0
        # can still be handled
        timeout_until = time_now + timeout

        while time_now <= timeout_until:
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

        raise RemotePlayerRecvTimeout()

    def __repr__(self):
        return "RemotePlayerConnection(%r)" % self.socket

class ZMQPublisher:
    """ Sets up a simple Publisher which sends all viewed events
    over a zmq connection.

    Parameters
    ----------
    address : string
        The address which the publisher binds or connects to.
    bind : bool
        Whether we are in bind or connect mode
    """
    def __init__(self, address, bind=True, zmq_context=None):
        self.address = address
        self.context = default_zmq_context(zmq_context)
        self.socket = self.context.socket(zmq.PUB)
        if bind:
            self.socket_addr = bind_socket(self.socket, self.address, '--publish')
            _logger.debug("Bound zmq.PUB to {}".format(self.socket_addr))
        else:
            self.socket.connect(self.address)
            _logger.debug("Connected zmq.PUB to {}".format(self.address))

    def _send(self, action, data):
        info = {'round': data['round'], 'turn': data['turn']}
        # TODO: this should be game_phase
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
        self.context = default_zmq_context(zmq_context)

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
