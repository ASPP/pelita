import yappi

from pelita.remote import TcpThreadedListeningServer
import threading

import Queue
import logging

log = logging.getLogger("jsonSocket")
log.setLevel(logging.DEBUG)
FORMAT = '[%(asctime)-15s][%(levelname)s][%(funcName)s] %(message)s'
logging.basicConfig(format=FORMAT)

endtimer = False

def show_num_threads():
    print "%d threads alive" % threading.active_count()
    t = threading.Timer(5, show_num_threads)
    if not endtimer:
        t.start()
t = threading.Timer(5, show_num_threads)
t.start()

#from actors.actor import Actor

from pelita.actors import SuspendableThread, RemoteActor, Response, Message
from pelita.remote.jsonconnection import MailboxConnection

class IncomingConnectionsActor(SuspendableThread):
    """This class merges the incoming messages of the forwarded connections."""
    def __init__(self, incoming_queue, forwarded):
        SuspendableThread.__init__(self)
        self.incoming_queue = incoming_queue
        self.forwarded = forwarded

        self.mailboxes = {}
        self._running = False

    def run(self):
        while self._running:
            try:
                # a new connection has been established
                conn = self.incoming_queue.get(True, 3)
                mailbox = MailboxConnection(conn, inbox=self.forwarded)
                self.mailboxes[conn] = mailbox
                mailbox.start()
            except Queue.Empty:
                continue

        # cleanup
        for conn, box in self.mailboxes.iteritems():
            box.stop()



players = []

class MyRemoteActor(RemoteActor):

    def receive(self, sender, msg):
        print msg.rpc
        if msg.method == "hello":
            players.append(sender)
            self.send(sender, Message("init", [0]))

        elif msg.method == "multiply":
            res = reduce(lambda x,y: x*y, msg.params)
            print "Calculated", res
            self.send(sender, Response(result=res, id=msg.id))


incoming_connections = Queue.Queue()

listener = TcpThreadedListeningServer(incoming_connections)
listener.start()

inbox = Queue.Queue()

incoming_bundler = IncomingConnectionsActor(incoming_connections, inbox)
incoming_bundler.start()

act = MyRemoteActor(inbox)
act.start()

import time
try:
    while 1:
        time.sleep(3)
        if len(players) >= 1:
            act.request(players[0], Message("next_move", {"state": []}))
except KeyboardInterrupt:
    print "Interrupted"
    act.stop()
    incoming_bundler.stop()
    s.stop()
    endtimer = True

#remote = remote_start(JsonThreadedListeningServer, "localhost", 9990).register_actor(RemoteActor)

# get with a timeout seems to eat cpu
# (http://blog.codedstructure.net/2011/02/concurrent-queueget-with-timeouts-eats.html)
# maybe we should kill threads using a special input value from top to bottom


