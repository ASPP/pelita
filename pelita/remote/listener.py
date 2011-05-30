from pelita.remote import TcpSocket

import Queue

from pelita.actors import SuspendableThread
import logging
import socket

import time

log = logging.getLogger("jsonSocket")
log.setLevel(logging.DEBUG)
FORMAT = '[%(asctime)-15s][%(levelname)s][%(funcName)s] %(message)s'
logging.basicConfig(format=FORMAT)


class TcpListeningSocket(TcpSocket):
    def __init__(self, address, port):
        super(TcpListeningSocket, self).__init__(address, port)
        self.socket.bind( (self.address, self.port) )
        self.socket.listen(1)

    def handle_accept(self):
        """Waits for a connection to be established and returns it."""
        connection, addr = self.socket.accept()
        log.info("Connection accepted.")
        connection.settimeout(3)
        return connection

class TcpThreadedListeningServer(SuspendableThread):
    def __init__(self, incoming_connections, address="localhost", port=10881):
        SuspendableThread.__init__(self)

        self.socket = TcpListeningSocket(address, port)
        self.socket.timeout = 3

        self.incoming_connections = incoming_connections

    def run(self):
        while self._running:
            try:
                connection = self.socket.handle_accept()
                self.incoming_connections.put(connection)
            except socket.timeout as e:
                log.debug("socket.timeout: %s" % e)
                continue
            except Exception as e:
                log.exception(e)
                continue


