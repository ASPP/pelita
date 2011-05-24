
import Queue


CONNECTIONS = Queue.Queue()

class JsonListeningServer(JsonSocket):
    def __init__(self, address, port):
        super(JsonListeningServer, self).__init__(address, port)
        self.socket.bind( (self.address, self.port) )
        self.socket.listen(1)

    def handle_accept(self):
        connection, addr = self.socket.accept()
        return JsonSocketConnection(connection)

class JsonThreadedListeningServer(threading.Thread, JsonListeningServer):
    def __init__(self, address="localhost", port=8881):
        threading.Thread.__init__(self)
        JsonListeningServer.__init__(self, address, port)

        self.socket.settimeout(3)
        self._running = False

    def run(self):
        while self._running:
            try:
                print "handle_accept"
                conn = self.handle_accept()
                CONNECTIONS.put(conn)
            except socket.timeout as e:
                logger.debug("socket.timeout: %s" % e)
                continue
            except Exception as e:
                logger.exception(e)
                continue
            

    def start(self):
        logger.info("Start listening server.")
        self._running = True
        threading.Thread.start(self)

    def stop(self):
        self._running = False

    def handle_accept(self):
        connection, addr = self.socket.accept()
        logger.info("Connection accepted.")
        return JsonThreadedSocketConnection(connection)

