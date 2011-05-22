import socket
import json

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
        self.socket.close()


class JsonSocket(object):
    def __init__(self, address, port):
        self.address = address
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # reuse socket
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

class JsonListeningServer(JsonSocket):
    def __init__(self, address="localhost", port=8881):
        super(JsonListeningServer, self).__init__(address, port)
        self.socket.bind( (self.address, self.port) )
        self.socket.listen(1)

    def handle_accept(self):
        connection, addr = self.socket.accept()
        return JsonSocketConnection(connection)

class JsonConnectingClient(JsonSocket):
    def __init__(self, address="localhost", port=8881):
        super(JsonConnectingClient, self).__init__(address, port)

    def handle_connect(self):
        connection = self.socket.connect((self.address, self.port))
        return JsonSocketConnection(self.socket)


if __name__ == "__main__":
    s = JsonListeningServer()
    serv = s.handle_accept()
    print serv.read()



