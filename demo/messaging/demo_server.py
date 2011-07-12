# -*- coding: utf-8 -*-

from pelita.messaging.remote import TcpThreadedListeningServer
import logging

import colorama
colorama.init()

FORMAT = '[%(asctime)s,%(msecs)03d][%(name)s][%(levelname)s][%(funcName)s]' + colorama.Fore.MAGENTA + ' %(message)s' + colorama.Fore.RESET
logging.basicConfig(format=FORMAT, datefmt="%H:%M:%S")

from pelita.messaging.utils.debug import ThreadInfoLogger
ThreadInfoLogger(10).start()

#from actors.actor import Actor

from pelita.messaging import Actor, Notification, DispatchingActor, dispatch, RemoteActorProxy, ActorProxy
from pelita.messaging.mailbox import MailboxConnection

class ServerActor(DispatchingActor):
    def __init__(self):
        super(ServerActor, self).__init__()

        self.mailboxes = {}
        self.players = []

    def stop_mailboxes(self):
        for conn, box in self.mailboxes.iteritems():
            box.stop()

    @dispatch(name="stop")
    def _stop(self, message=None):
        """Stops the actor."""
        self.stop()

    def on_stop(self):
        self.stop_mailboxes()

    @dispatch
    def multiply(self, message, *args):
        """Multiplies the argument list."""
        res = reduce(lambda x,y: x*y, args)
        print "Calculated", res
        return res

    @dispatch
    def hello(self, message, *args):
        self.players.append(message.mailbox)
        message.mailbox.put(Notification("init", [0]))

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
            player = RemoteActorProxy(self.players[ac_num])

            start_val = iterations * ac_num
            stop_val = iterations * (ac_num + 1) - 1

            # pi
            req = player.query("calculate_pi_for", [start_val, stop_val])
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

    @dispatch
    def minigame(self, message):
        """Demos a small game."""
        if len(self.players) != 2:
            message.reply_error("Need two players.")
            return

        reqs = []

        for player in self.players:
            player = RemoteActorProxy(player)
            reqs.append( player.query("random_int", []) )

        res = 0
        for answer in reqs:
            res += answer.get().result

        if res % 2 != 0:
            message.reply("Player 1 wins")
        else:
            message.reply("Player 2 wins")

import inspect

def actorOf(actor):
    if inspect.isclass(actor):
        actor = actor()
    return ActorProxy(actor)

actor_ref = actorOf(ServerActor)
actor_ref.start()

listener = TcpThreadedListeningServer(host="", port=50007)

mailboxes = []

def accepter(connection):
    # a new connection has been established
    mailbox = MailboxConnection(connection, main_actor=actor_ref) # which actor?
    mailboxes[connection] = mailbox
    mailbox.start()

listener.on_accept = accepter
listener.start()

class Remote(object):
    def __init__(self):
        self.listener = None

        self.reg = {}

    def start_listener(self, host, port):
        self.listener = TcpThreadedListeningServer(host=host, port=port)
        return self

    def register(self, actor_name, actor_ref):
        self.reg[actor_name] = actor_ref
        return self

    def start_all(self):
        for ref in self.reg.values():
            ref.start()


remote = Remote().start_listener("localhost", 9999)

remote.register("main-actor", actorOf(ServerActor))
remote.start_all()


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
        split_inp = inp.partition(" ")
        method = split_inp[0]
        json_params = split_inp[2].strip()

        if not method.strip():
            continue

        try:
            if json_params:
                params = json.loads(json_params)
            else:
                params = []
        except ValueError:
            print "value error"
            continue

        try:
            if len(params):
                req = actor_ref.query(method, params).get()
            else:
                req = actor_ref.query(method).get()
        except TypeError:
            print "Need to get list"
            continue

        try:
            print req.result
        except AttributeError:
            print req.error

except (KeyboardInterrupt, EndSession):
    print "Interrupted"

    req =  actor_ref.stop()
#    actor.stop()
    listener.stop()
    import sys
    sys.exit()

#remote = remote_start(JsonThreadedListeningServer, "localhost", 9990).register_actor(RemoteActor)

# get with a timeout seems to eat cpu
# (http://blog.codedstructure.net/2011/02/concurrent-queueget-with-timeouts-eats.html)
# maybe we should kill threads using a special input value from top to bottom


