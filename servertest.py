# -*- coding: utf-8 -*-
from pelita.remote import TcpThreadedListeningServer
import threading

import Queue
import logging

import colorama
colorama.init()

FORMAT = '[%(asctime)s,%(msecs)03d][%(name)s][%(levelname)s][%(funcName)s]' + colorama.Fore.MAGENTA + ' %(message)s' + colorama.Fore.RESET
logging.basicConfig(format=FORMAT, datefmt="%H:%M:%S")

from pelita.utils.debug import ThreadInfoLogger
ThreadInfoLogger(10).start()

#from actors.actor import Actor

from pelita.utils import SuspendableThread

from pelita.actors import Actor, RemoteActor, Response, Message, Query
from pelita.remote.mailbox import MailboxConnection


def sendable(fun):
    fun.sendable = True
    return fun

class ServerActor(Actor):
    def __init__(self):
        super(ServerActor, self).__init__()

        self.mailboxes = {}
        self.players = []

    def receive(self, message):
        super(ServerActor, self).receive(message)

        self._dispatcher(message)

    def _dispatcher(self, message):
        # call method directly on actor (unsafe)
        method = message.method
        params = message.params

        def reply_error(msg):
            try:
                message.reply_error(msg)
            except AttributeError:
                pass

        wants_doc = False
        if method[0] == "?":
            method = method[1:]
            wants_doc = True

        meth = getattr(self, method, None)
        if not meth:
            reply_error("Not found: method '{0}'".format(message.method))
            return

        if not getattr(meth, "sendable", False):
            reply_error("Not sendable: method '{0}'".format(message.method))
            return

        if wants_doc:
            if hasattr(message, "reply"):
                res = meth.__doc__
                message.reply(res)
            return

        if params is None:
            params = []

        try:
            res = meth(message, *params)
        except TypeError:
            reply_error("Type Error: method '{0}'".format(message.method))
            return

        if hasattr(message, "reply"):
            message.reply(res)

    def stop_mailboxes(self):
        for conn, box in self.mailboxes.iteritems():
            box.stop()

#
# Messages we accept
# TODO: It is still unclear where to put the arguments 
# and where to put the sender/message object
#
# a)
#   def method(self, message, arg1, *args):
#       sender = message.sender
#       message.reply(...)
#
# b)
#   def method(self, arg1, *args):
#       self.sender         # set in the loop before, quasi global
#       self.reply(...)     # set in the loop before, quasi global
#
# c)
#   def method(self, message):
#       args = message.params
#       sender = message.sender
#       message.reply(...)
#
# d)
#   use inner functions inside receive()
#

    @sendable
    def add_mailbox(self, message, conn):
        # a new connection has been established
        mailbox = MailboxConnection(conn, inbox=self) # TODO or self._inbox?
        self.mailboxes[conn] = mailbox
        mailbox.start()

    @sendable
    def stop(self, message=None):
        self.stop_mailboxes()
        super(ServerActor, self).stop()

    @sendable
    def multiply(self, message, *args):
        """Multiplies the argument list."""
        res = reduce(lambda x,y: x*y, args)
        print "Calculated", res
        return res

    @sendable
    def hello(self, message, *args):
        self.players.append(message.mailbox)
        message.mailbox.put(Message("init", [0]))

    @sendable
    def players(self, message, *args):
        message.reply(list(self.players))

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
    """Using a helper function to get coloured output (not working with logging...)"""
    print colorama.Fore.BLUE + str(msg) + colorama.Fore.RESET

class EndSession(Exception):
    pass

NUM_NEEDED_ACTORS = 1

MAX_NUMBER_PER_AC = 10000000

import time

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

try:
    printcol("Waiting for actors to be available.")
    while 1:
        time.sleep(3)
        players = actor.request("players").get().result
        if len(players) >= NUM_NEEDED_ACTORS:
            printcol("Actors are available.")
            answers = []

            for ac_num in range(NUM_NEEDED_ACTORS):
                player = RemoteActor(players[ac_num])

                start_val = MAX_NUMBER_PER_AC * ac_num
                stop_val = MAX_NUMBER_PER_AC * (ac_num + 1) - 1

                # pi
                req = player.request("calculate_pi_for", [start_val, stop_val])
                printcol(req)
                answers.append( req )

                # slow series
#                if start_val == 0:
#                    start_val = 2
#                answers.append( player.request("slow_series", [start_val, stop_val]) )

            res = 0
            for answer in answers:
                print answer
                res += answer.get().result

            printcol("Result: " + str(res))
            raise EndSession()

except (KeyboardInterrupt, EndSession):
    print "Interrupted"

    req =  actor.request("stop").get()
    try:
        print req.result
    except AttributeError:
        print req.error
    actor.stop()
    listener.stop()

#remote = remote_start(JsonThreadedListeningServer, "localhost", 9990).register_actor(RemoteActor)

# get with a timeout seems to eat cpu
# (http://blog.codedstructure.net/2011/02/concurrent-queueget-with-timeouts-eats.html)
# maybe we should kill threads using a special input value from top to bottom


