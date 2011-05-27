import yappi
yappi.start() # start the profiler

from pelita.remote.listening_server import JsonThreadedListeningServer, q_connections
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


s = JsonThreadedListeningServer()
s.start()


#from actors.actor import Actor
import threading

from pelita.actors.actor import SuspendableThread

from pelita.remote.jsonconnection import MailboxConnection

class IncomingConnectionsActor(SuspendableThread):
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


inbox = Queue.Queue()

incoming_bundler = IncomingConnectionsActor(q_connections, inbox)
incoming_bundler.start()


class RemoteActor(SuspendableThread):
    def __init__(self, inbox):
        SuspendableThread.__init__(self)
        self._inbox = inbox

    def _run(self):
        try:
            sender, msg = self._inbox.get(True, 3)
            self.receive(sender, msg)
        except Queue.Empty:
            pass

    def receive(self, sender, msg):
        log.debug("Received sender %s msg %s", sender, msg)
        if sender == self:
            print "SELF"
        else:
            sender.put({"method": "hello", "params": "12345"})

act = RemoteActor(inbox)
act.start()


#remote = remote_start(JsonThreadedListeningServer, "localhost", 9990).register_actor(RemoteActor)



import time
try:
    while 1:
        time.sleep(10)
except KeyboardInterrupt:
    print "Interrupted"
    act.stop()
    incoming_bundler.stop()
    s.stop()
    endtimer = True


