from pelita.remote.rpcsocket import JsonSocket

import Queue

from pelita.actors.actor import SuspendableThread
import logging
import socket

import time

log = logging.getLogger("jsonSocket")
log.setLevel(logging.DEBUG)
FORMAT = '[%(asctime)-15s][%(levelname)s][%(funcName)s] %(message)s'
logging.basicConfig(format=FORMAT)


q_connections = Queue.Queue()

class JsonListeningServer(JsonSocket):
    def __init__(self, address, port):
        super(JsonListeningServer, self).__init__(address, port)
        self.socket.bind( (self.address, self.port) )
        self.socket.listen(1)

    def handle_accept(self):
        connection, addr = self.socket.accept()
        log.info("Connection accepted.")

        q_connections.put(connection)

class JsonThreadedListeningServer(SuspendableThread, JsonListeningServer):
    def __init__(self, address="localhost", port=8881):
        SuspendableThread.__init__(self)
        JsonListeningServer.__init__(self, address, port)

        self.socket.settimeout(3)

    def run(self):
        while self._running:
            try:
                self.handle_accept()
            except socket.timeout as e:
                log.debug("socket.timeout: %s" % e)
                continue
            except Exception as e:
                log.exception(e)
                continue


