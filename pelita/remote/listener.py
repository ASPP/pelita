# -*- coding: utf-8 -*-

from pelita.remote import TcpSocket

import Queue

import logging
import socket

import time

from pelita.utils import SuspendableThread

_logger = logging.getLogger("pelita.listener")
_logger.setLevel(logging.INFO)

class TcpListeningSocket(TcpSocket):
    def __init__(self, host, port):
        super(TcpListeningSocket, self).__init__(host, port)

        self.socket.bind( (self.host, self.port) )
        self.socket.listen(1)

    def handle_accept(self):
        """Waits for a connection to be established and returns it."""
        connection, addr = self.socket.accept()
        _logger.info("Connection accepted.")
        connection.settimeout(3)
        return connection

class TcpThreadedListeningServer(SuspendableThread):
    def __init__(self, incoming_connections, host, port):
        SuspendableThread.__init__(self)

        self.socket = TcpListeningSocket(host, port)
        self.socket.timeout = 3

        self.incoming_connections = incoming_connections

    def run(self):
        while self._running:
            try:
                connection = self.socket.handle_accept()
                self.incoming_connections.put(connection)
            except socket.timeout as e:
                _logger.debug("socket.timeout: %s" % e)
                continue
            except Exception as e:
                _logger.exception(e)
                continue


