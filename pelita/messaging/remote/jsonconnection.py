# -*- coding: utf-8 -*-

import socket
import json
import errno
import logging

from pelita.messaging import Error, DeadConnection, BaseMessage

_logger = logging.getLogger("pelita.jsonSocket")
_logger.setLevel(logging.INFO)


class JsonSocketConnection(object):
    """Implements a socket for JSON communication."""
    def __init__(self, connection):
        self.connection = connection

        # Set a timeout so that it is possible to interact with the socket
        self.connection.settimeout(3)

        # Our terminator must never be included in our JSON strings
        # also, it must be a one-byte character for easier parsing
        self._terminator = "\x04" # End of transmission

        self.buffer = []
        self.incoming = ""

    @property
    def terminator(self):
        return self._terminator

    @terminator.setter
    def terminator(self, value):
        if len(value) != 1:
            raise RuntimeError("Terminator length must be 1.")
        self._terminator = value

    def send(self, obj):
        if self.connection:
            json_string = json.dumps(obj)
            self._send(json_string)
        else:
            raise RuntimeError("Cannot send without a connection.")

    def _send(self, json_string):
        if self.terminator in json_string:
            raise RuntimeError("JSON contains invalid termination character.")

        data = json_string + self.terminator

        sent_bytes = 0
        while sent_bytes < len(data):
            _logger.info("Sending raw data %s", data[sent_bytes:])
            sent_bytes += self.connection.send(data[sent_bytes:])

    def _read(self):
        try:
            data = self.connection.recv(4096)
            _logger.debug("Got raw data %s", data)
        except socket.timeout:
            _logger.debug("Socket timed out, repeating.")
            return
        except socket.error as e: # shouldn't that be errno, errmsg?
            if e.args[0] in (errno.EBADF,):
                # close
                _logger.info("Connection is dead.")
                raise DeadConnection()

            _logger.warning("Caught an unknown error in recv. Sleep and try to repeat.")
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

    def read(self):
        # collect data until there is an object in buffer
        while not self.buffer:
            self._read()

        # get the first element
        data = self.buffer.pop(0)
        json_data = json.loads(data)
        _logger.debug("Data read %s", json_data)
        return json_data

    def close(self):
        self.connection.close()


class JsonRPCSocketConnection(JsonSocketConnection):
    """Implements a socket for JSON-RPC communication."""
    def __init__(self, connection):
        super(JsonRPCSocketConnection, self).__init__(connection)

    def send(self, message):
        if not isinstance(message, BaseMessage):
            raise ValueError("'%s' is no Message object." % message)

        super(JsonRPCSocketConnection, self).send(message.dict)

    def read(self):
        obj = super(JsonRPCSocketConnection, self).read()
        _logger.debug("Received: %s", obj)
        try:
            msg_obj = BaseMessage.load(obj)
        except ValueError:
            msg_obj = Error("wrong input", None)

        return msg_obj

