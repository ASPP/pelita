import yappi
yappi.start() # start the profiler

from pelita.remote.listening_server import JsonThreadedListeningServer, CONNECTIONS
import threading

import Queue

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

from pelita.remote.jsonconnection import MailboxConnection

connections = []
mailboxes = {}

inbox = Queue.Queue()

while 1:
    while 1:
        try:
            connections.append(CONNECTIONS.get(False))
        except Queue.Empty:
            break

    for conn in connections:
        if conn in mailboxes:
            pass
        else:
            mailboxes[conn] = MailboxConnection(conn, inbox=inbox)
            mailboxes[conn].start()

#    for conn, mailb in mailboxes.iteritems():
    try:
        print inbox.qsize()
        res = inbox.get(True, 1)
        for conn, mb in mailboxes.iteritems():
            if res[0] == conn:
                print "SELF"
            else:
                mb.put({"method": "hello", "params": "12345"})

    except Queue.Empty:
        res = "None"
    print "RES", res
#        if res[1].method == "shutdown":
#            print "EXIT"
#            a.stop()
#            exit()

    #cq = JsonThreadedSocketConnection(conn)
    #cq.start()
    #cq.join()


while 1:
    y = raw_input("yappi>")
    exec y


