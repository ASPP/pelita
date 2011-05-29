import socket
import logging

class TcpSocket(object):
    def __init__(self, address, port):
        self._address = address
        self._port = port
        # a TCP socket
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # make socket reusable
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.setblocking(1)

    @property
    def address(self):
        return self._address

    @property
    def port(self):
        return self._port

    @property
    def socket(self):
        return self._socket

    @property
    def timeout(self):
        """Changes the timeout of the socket."""
        return self._socket.gettimeout()

    @timeout.setter
    def timeout(self, value):
        self._socket.settimeout(value)

    def connect(self):
        """Connects the socket with the provided address and return the connection."""
        self._socket.connect( (self._address, self._port) )


class TcpConnectingClient(TcpSocket):
    def __init__(self, address="localhost", port=8881):
        super(TcpConnectingClient, self).__init__(address, port)
        self.timeout = 3

    def handle_connect(self):
        connection = self.connect()
        return self.socket # JsonSocketConnection(self.socket)



