import yappi
yappi.start() # start the profiler

from pelita.remote.listening_server import JsonThreadedListeningServer, CONNECTIONS
import threading


def show_num_threads():
    print "%d threads alive" % threading.active_count()
    t = threading.Timer(5, show_num_threads)
    t.start()
t = threading.Timer(5, show_num_threads)
t.start()


s = JsonThreadedListeningServer()
s.start()


#from actors.actor import Actor
import threading



class RemoteActor(threading.Thread):
    @property
    def remote(self):
        return self._remote

    @remote.setter
    def remote(self, value):
        self._remote = value

    def start(self):
        self.remote.start()

    def stop(self):
        self.remote.stop()

    def send(self, msg):
        self.remote.send(msg)

    def request(self, msg):
        return self.remote.request(msg)

    def request_recv(self, msg, timeout=0):
        return self.request(msg).get(timeout)

while 1:
    from pelita.remote.jsonconnection import MailboxConnection
    conn = CONNECTIONS.get()
#    a = RemoteActor()
#    a.remote = JsonThreadedMailboxSocketConnection(conn)
#    a.start()
    a = MailboxConnection(conn)
    a.start()
    while 1:
        print a.get()

    #cq = JsonThreadedSocketConnection(conn)
    #cq.start()
    #cq.join()


while 1:
    y = raw_input("yappi>")
    exec y


