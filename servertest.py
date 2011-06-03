import yappi

from pelita.remote import TcpThreadedListeningServer
import threading

import Queue
import logging

BLUE = '\033[94m'
ENDC = '\033[0m'

_log = logging.getLogger("servertest")
_log.setLevel(logging.DEBUG)
FORMAT = '[%(asctime)-15s][%(levelname)s][%(funcName)s] '+BLUE+'%(message)s'+ENDC
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

from pelita.actors import SuspendableThread, RemoteActor, Response, Message, Query
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

actor = MyRemoteActor(inbox)
actor.start()

def printcol(msg):
    """Using a helper function to get coloured output (not working with logging...)"""
    print BLUE+ msg +ENDC

class EndSession(Exception):
    pass

NUM_NEEDED_ACTORS = 1

MAX_NUMBER_PER_AC = 1000000

import time
try:
    printcol("Waiting for actors to be available.")
    while 1:
        time.sleep(3)
        if len(players) >= NUM_NEEDED_ACTORS:
            answers = []

            for ac_num in range(NUM_NEEDED_ACTORS):
                player = players[ac_num]

                start_val = MAX_NUMBER_PER_AC * ac_num
                stop_val = MAX_NUMBER_PER_AC * (ac_num + 1) - 1
                
                # pi
                answers.append( actor.request(player, Query("calculate_pi_for", [start_val, stop_val], id=None)) )

                # slow series
#                if start_val == 0:
#                    start_val = 2
#                answers.append( actor.request(player, Query("slow_series", [start_val, stop_val], id=None)) )
            
            res = 0
            for answer in answers:
                print answer
                res += answer.get().result

            printcol("Result: " + str(res))
            raise EndSession

except KeyboardInterrupt, EndSession:
    print "Interrupted"
    actor.stop()
    incoming_bundler.stop()
    listener.stop()
    endtimer = True

#remote = remote_start(JsonThreadedListeningServer, "localhost", 9990).register_actor(RemoteActor)

# get with a timeout seems to eat cpu
# (http://blog.codedstructure.net/2011/02/concurrent-queueget-with-timeouts-eats.html)
# maybe we should kill threads using a special input value from top to bottom


