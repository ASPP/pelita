# -*- coding: utf-8 -*-

import logging
import socket

from . import TcpSocket
from ...utils import SuspendableThread

_logger = logging.getLogger("pelita.listener")

__docformat__ = "restructuredtext"


class TcpListeningSocket(TcpSocket):
    def __init__(self, host, port):
        """ Opens a socket with respective host and port
        and listens for an incoming connection.
        """

        super(TcpListeningSocket, self).__init__(host, port)

        self.socket.bind( (self._host, self._port) )
        self.socket.listen(1)

    def handle_accept(self):
        """ Waits for a connection to be established and returns it."""
        connection, addr = self.socket.accept()
        _logger.info("Connection accepted.")

        return connection

class TcpThreadedListeningServer(SuspendableThread):
    def __init__(self, host, port):
        """ Opens a socket with respective host and port
        and listens for an incoming connection.

        Each instantiation must supply its own on_accept()
        method which specifies what action needs to be done
        when a new connection is established.
        """
        super(TcpThreadedListeningServer, self).__init__()

        self.socket = TcpListeningSocket(host, port)

        # if there is a problem with closing, enable the timeout
        # self.socket.timeout = 3
        _logger.info("%r: Created socket" % self)

    def run(self):
        while self._running:
            try:
                connection = self.socket.handle_accept()

                # we waited so long, we need to see that we're still alive
                # if it was a dummy connection, we will return now
                if not self._running:
                    return

                # okay, we are alive (unless, of course, we died in between)
                # handle the new connection
                self.on_accept(connection)

            except socket.timeout as e:
                _logger.debug("socket.timeout: %r" % e)
                continue

            except Exception as e:
                _logger.exception(e)
                continue

    def on_accept(self, connection):
        raise NotImplementedError

    def stop(self):
        super(TcpThreadedListeningServer, self).stop()

        # To stop listening, we create a dummy connection
        # and close it immediately
        dummy = socket.socket()
        dummy.connect((self.socket.host, self.socket.port))
        dummy.close()

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self.socket)

class TcpThreadedListeningServerQueuer(TcpThreadedListeningServer):
    def __init__(self, incoming_connections, host, port):
        super(TcpThreadedListeningServerQueuer, self).__init__(host, port)

        self.incoming_connections = incoming_connections

    def on_accept(self, connection):
        _logger.info("%r: Got connection request %r" % (self, connection))
        self.incoming_connections.put(connection)


