# -*- coding: utf-8 -*-

import socket

__docformat__ = "restructuredtext"


class TcpSocket(object):
    """ Wraps a socket for a TCP connection.

    The socket is initially set to blocking. This may be changed using
     the `timeout` property.
    """
    def __init__(self, host, port):
        self._host = host
        self._port = port
        # a TCP socket
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # make socket reusable
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.setblocking(1)

    @property
    def host(self):
        return self._socket.getsockname()[0]

    @property
    def port(self):
        return self._socket.getsockname()[1]

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
        self._socket.connect( (self._host, self._port) )

    def close(self):
        """Closes the socket"""
        self._socket.close()

    def __repr__(self):
        try:
            host = self._socket.getsockname()
            connection = "%s:%s" % (host)
        except socket.error:
            connection = "none"

        return "%s(%s)" % (self.__class__.__name__, connection)


class TcpConnectingClient(TcpSocket):
    def __init__(self, host, port):
        super(TcpConnectingClient, self).__init__(host, port)
        self.timeout = 3

    def handle_connect(self):
        self.connect()
        self.timeout = 3
        return self.socket # or JsonSocketConnection(self.socket) ?



