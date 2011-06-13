# -*- coding: utf-8 -*-

from pelita.remote import TcpThreadedListeningServer
import logging

import colorama
colorama.init()

FORMAT = '[%(asctime)s,%(msecs)03d][%(name)s][%(levelname)s][%(funcName)s]' + colorama.Fore.MAGENTA + ' %(message)s' + colorama.Fore.RESET
logging.basicConfig(format=FORMAT, datefmt="%H:%M:%S")

from pelita.utils.debug import ThreadInfoLogger
ThreadInfoLogger(10).start()

#from actors.actor import Actor

from pelita.actors import Actor, RemoteActor, Message, DispatchingActor, dispatch
from pelita.remote.mailbox import MailboxConnection

class ServerActor(DispatchingActor):
    def __init__(self):
        super(ServerActor, self).__init__()

        self.mailboxes = {}
        self.players = []

    def stop_mailboxes(self):
        for conn, box in self.mailboxes.iteritems():
            box.stop()

    @dispatch
    def add_mailbox(self, message, conn):
        # a new connection has been established
        mailbox = MailboxConnection(conn, inbox=self) # TODO or self._inbox?
        self.mailboxes[conn] = mailbox
        mailbox.start()

    @dispatch(name="stop")
    def _stop(self, message=None):
        """Stops the actor."""
        self.stop()

    def stop(self):
        self.stop_mailboxes()
        super(ServerActor, self).stop()

    @dispatch
    def multiply(self, message, *args):
        """Multiplies the argument list."""
        res = reduce(lambda x,y: x*y, args)
        print "Calculated", res
        return res

    @dispatch
    def hello(self, message, *args):
        self.players.append(message.mailbox)
        message.mailbox.put(Message("init", [0]))

    @dispatch(name="players")
    def _players(self, message, *args):
        message.reply(list(self.players))


    @dispatch
    def calc(self, message, num_clients=1, iterations=10000):
        if len(list(self.players)) < num_clients:
            message.reply_error("Not enough clients connected")
            return

        answers = []

        for ac_num in range(num_clients):
            player = RemoteActor(self.players[ac_num])

            start_val = iterations * ac_num
            stop_val = iterations * (ac_num + 1) - 1

            # pi
            req = player.request("calculate_pi_for", [start_val, stop_val])
            printcol(req)
            answers.append( req )

            # slow series
#           if start_val == 0:
#               start_val = 2
#           answers.append( player.request("slow_series", [start_val, stop_val]) )

        res = 0
        for answer in answers:
            res += answer.get().result
        message.reply(res)


actor = ServerActor()
actor.start()

listener = TcpThreadedListeningServer(host="", port=50007)
def accepter(connection):
    actor.send("add_mailbox", [connection])
listener.on_accept = accepter
listener.start()


#incoming_bundler = IncomingConnectionsActor(incoming_connections, inbox)
#incoming_bundler.start()

def printcol(msg):
    """Using a helper function to get coloured output"""
    print colorama.Fore.BLUE + str(msg) + colorama.Fore.RESET

class EndSession(Exception):
    pass

import json
try:
    while True:
        inp = raw_input("> ")
        splitted_inp = inp.partition(" ")
        method = splitted_inp[0]
        try:
            params = json.loads(splitted_inp[2])
        except ValueError:
            params = []

        if len(params):
            req = actor.request(method, params).get()
        else:
            req = actor.request(method).get()

        try:
            print req.result
        except AttributeError:
            print req.error

except (KeyboardInterrupt, EndSession):
    print "Interrupted"

    req =  actor.request("stop")
#    actor.stop()
    listener.stop()
    import sys
    sys.exit()

#remote = remote_start(JsonThreadedListeningServer, "localhost", 9990).register_actor(RemoteActor)

# get with a timeout seems to eat cpu
# (http://blog.codedstructure.net/2011/02/concurrent-queueget-with-timeouts-eats.html)
# maybe we should kill threads using a special input value from top to bottom


