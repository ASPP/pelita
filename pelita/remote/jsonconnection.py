import socket
import json
import threading

import logging

log = logging.getLogger("jsonSocket")
log.setLevel(logging.DEBUG)
FORMAT = '[%(asctime)-15s][%(levelname)s][%(funcName)s] %(message)s'
logging.basicConfig(format=FORMAT)

class DeadConnection(Exception):
    pass

class JsonSocketConnection(object):
    """Implements a socket for JSON-RPC communication."""
    def __init__(self, connection):
        self.connection = connection

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
            sent_bytes += self.connection.send(data[sent_bytes:])

    def _read(self):
        data = self.connection.recv(4096)

        if not data:
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

        # get the first elemet
        data = self.buffer.pop(0)
        json_data = json.loads(data)
        log.debug("Data read %s", json_data)
        return json_data

    def close(self):
        self.connection.close()


class JsonThreadedSocketConnection(threading.Thread, JsonSocketConnection):
    def __init__(self, connection):
        threading.Thread.__init__(self)
        JsonSocketConnection.__init__(self, connection)

        self.connection.settimeout(3)
        self._running = False

    def run(self):
        while self._running:
            try:
                print "read"
                obj = self.read()
                print obj
            except socket.timeout as e:
                log.debug("socket.timeout: %s" % e)
                continue
            except DeadConnection:
                self.close()
                self._running = False
            except Exception as e:
                log.exception(e)
                continue

        log.info("End socket connection server.")

    def start(self):
        log.info("Start socket connection server.")
        self._running = True
        threading.Thread.start(self)

    def stop(self):
        self._running = False

