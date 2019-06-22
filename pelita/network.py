
import logging

import json
import time
import zmq

from .simplesetup import bind_socket

_logger = logging.getLogger(__name__)

class Controller:
    def __init__(self, address='tcp://127.0.0.1:*', zmq_context=None):
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
