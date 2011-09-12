# -*- coding: utf-8 -*-

import socket
import errno
import logging

from .. import Error, DeadConnection, BaseMessage
from ..json_convert import json_converter

_logger = logging.getLogger("pelita.jsonSocket")
_logger.setLevel(logging.INFO)

__docformat__ = "restructuredtext"


class JsonSocketConnection(object):
    """ Implements JSON communication over a socket.

    The socket may send any object which can be (trivially)
    converted to a JSON string by calling `json.dumps(obj)`.

    The string is then sent over a socket connection and
    terminated with a special termination character.

    By default, this character is EOT (= End of transmission, \x04),
    which of course must never occur in a JSON string.
    """
    def __init__(self, socket):
        self.socket = socket

        # Set a timeout so that it is possible to interact with the socket
        self.socket.settimeout(3)

        # Our terminator must never be included in our JSON strings
        # also, it must be a one-byte character for easier parsing
        self._terminator = "\x04" # End of transmission

        # the buffer is used for complete JSON strings
        # which have not yet been popped by `read()`
        self.buffer = []

        # the incoming string is used for the last incomplete JSON string
        # which still waits for completion
        self.incoming = ""

    @property
    def terminator(self):
        """ Accessor for the JSON termination character.

        The character must be a single character and must not be
        included in the submitted JSON string.
        """
        return self._terminator

    @terminator.setter
    def terminator(self, value):
        if len(value) != 1:
            raise ValueError("Terminator length must be 1.")
        self._terminator = value

    def send(self, obj):
        """ Converts `obj` to a json string and sends it.
        """
        if self.socket:
            json_string = json_converter.dumps(obj)
            try:
                self._send(json_string)
            except socket.error:
                raise DeadConnection
        else:
            raise RuntimeError("Cannot send without a connection.")

    def _send(self, json_string):
        """ Takes a json_string, appends the termination character
        and sends it.
        """
        if self.terminator in json_string:
            raise ValueError("JSON contains invalid termination character.")

        data = json_string + self.terminator

        sent_bytes = 0
        while sent_bytes < len(data):
            _logger.info("Sending raw data %r", data[sent_bytes:])
            sent_bytes += self.socket.send(data[sent_bytes:])

    def read(self):
        """ This method waits until new data is available at the connection
        or in the buffer and returns it to the caller.
        """
        # collect data until there is an object in buffer
        while not self.buffer:
            self._read()

        # get the first element
        data = self.buffer.pop(0)
        try:
            json_data = json_converter.loads(data)
            _logger.debug("Data read %r", json_data)
        except ValueError:
            _logger.warning("Could not decode data %r", data)
            raise

        return json_data

    def _read(self):
        """ Waits until the next chunk of data can be received
        and processes it.

        We can only receive a small chunk of the data at once.
        Even though TCP guarantees, that all chunks follow in order
        and no chunk of data is lost, the data may have been split
        on its way here.
        This is why we are collecting it in our buffers.
        """
        try:
            data = self.socket.recv(4096)
            _logger.debug("Got raw data %r", data)
        except socket.timeout:
            _logger.debug("Socket timed out, repeating.")
            return
        except socket.error as e: # shouldn't that be errno, errmsg?
            if e.args[0] in (errno.EBADF,):
                # close
                _logger.info("Connection is dead.")
                raise DeadConnection()

            _logger.warning("Caught an unknown error in socket.recv. Sleep and try to repeat.")
            _logger.warning(e)
            # Waiting a bit
            import time
            time.sleep(1)
            return

        if not data:
            # recv returns "", if the connection has been closed
            # this connection seems to be dead
            raise DeadConnection()

        split_data = data.split(self.terminator)
        # we split the data to get the following:
        # [contd*, full*, incomplete]

        # the last part is always incomplete or empty
        incomplete = split_data[-1]
        complete = split_data[:-1]

        if complete:
            # the first element of complete is the continued
            # incoming object of the last _read
            contd = complete.pop(0)
            self.incoming += contd
            self.buffer.append(self.incoming)
            self.incoming = ""

        if complete:
            # if there is still something left in complete,
            # move everything to the buffer
            self.buffer += complete
            # we throw away complete to make clear we have
            # collected all data
            complete = []

        # append the incomplete data to the incoming string
        self.incoming += incomplete

    def close(self):
        self.socket.close()

    def is_connected(self):
        """ Returns true, if we can receive the socket's peername.
        Otherwise, we'll assume that the socket is not connected.
        """
        try:
            peer = self.socket.getpeername()
            return True
        except socket.error:
            return False

    def __repr__(self):
        try:
            host = self.socket.getsockname()
            peer = self.socket.getpeername()
            connection = "%s -> %s" % (host, peer)
        except socket.error:
            connection = "none"

        return "JsonSocketConnection(%s)" % connection


class MessageSocketConnection(JsonSocketConnection):
    """ Implements a socket for JSON-RPC communication with pre-defined messages.

    """
    def send(self, message):
        if not isinstance(message, BaseMessage):
            raise ValueError("'%r' is no Message object." % message)

        super(MessageSocketConnection, self).send(message.dict)

    def read(self):
        try:
            obj = super(MessageSocketConnection, self).read()
            _logger.debug("Received: %r", obj)
        except ValueError:
            # Reply an error code -32700
            error_msg = {"message": "Parse Error",
                         "code": -32700,
                         "data": ["No valid json"]
                        }
            return Error(error_msg, None)

        # okay, the code was valid json.
        # see, if it is a valid message
        try:
            msg_obj = BaseMessage.load(obj)
        except ValueError:
            # Reply an error code -32700
            error_msg = {"message": "Parse Error",
                         "code": -32700,
                         "data": ["No valid message", obj]
                         }
            return Error(error_msg, None)

        return msg_obj

