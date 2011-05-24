import socket
import json
import threading

import logging

logger = logging.getLogger("jsonSocket")
logger.setLevel(logging.DEBUG)
FORMAT = '[%(asctime)-15s][%(levelname)s][%(funcName)s] %(message)s'
logging.basicConfig(format=FORMAT)

class DeadConnection(RuntimeError):
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
        return json.loads(data)

    def close(self):
        self.connection.close()


class JsonSocket(object):
    def __init__(self, address, port):
        self.address = address
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # reuse socket
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)


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
                logger.debug("socket.timeout: %s" % e)
                continue
            except DeadConnection:
                self.close()
                self._running = False
            except Exception as e:
                logger.exception(e)
                continue

    def start(self):
        logger.info("Start socket connection server.")
        self._running = True
        threading.Thread.start(self)

    def stop(self):
        self._running = False

class JsonConnectingClient(JsonSocket):
    def __init__(self, address="localhost", port=8881):
        super(JsonConnectingClient, self).__init__(address, port)
        self.socket.settimeout(3)

    def handle_connect(self):
        connection = self.socket.connect((self.address, self.port))
        return JsonSocketConnection(self.socket)


if __name__ == "__main__":
    import yappi
    yappi.start() # start the profiler

    s = JsonThreadedListeningServer()
    s.start()

    def show_num_threads():
        logger.info("%d threads alive", threading.active_count())
        t = threading.Timer(5, show_num_threads)
        t.start()

    t = threading.Timer(5, show_num_threads)
    t.start()

    while 1:
        y = raw_input("yappi>")
        exec y



