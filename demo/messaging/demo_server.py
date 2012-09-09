# -*- coding: utf-8 -*-

import logging

from pelita.utils.colorama_wrapper import colorama
from functools import reduce

FORMAT = '[%(asctime)s,%(msecs)03d][%(name)s][%(levelname)s][%(funcName)s]' + colorama.Fore.MAGENTA + ' %(message)s' + colorama.Fore.RESET
logging.basicConfig(format=FORMAT, datefmt="%H:%M:%S")

from pelita.utils.debug import ThreadInfoLogger
ThreadInfoLogger(10).start()

from pelita.messaging import Actor, DispatchingActor, expose, actor_of, RemoteConnection

class ServerActor(DispatchingActor):
    def __init__(self):
        super(ServerActor, self).__init__()

        self.mailboxes = {}
        self.players = []

    def stop_mailboxes(self):
        for conn, box in self.mailboxes.items():
            box.stop()

    @expose(name="stop")
    def _stop(self):
        """Stops the actor."""
        self.stop()

    def on_stop(self):
        self.stop_mailboxes()

    @expose
    def multiply(self, *args):
        """Multiplies the argument list."""
        res = reduce(lambda x,y: x*y, args)
        print("Calculated", res)
        self.ref.reply(res)

    @expose
    def hello(self, actor_uuid):

        proxy = self.ref.remote.create_proxy(actor_uuid)
        self.players.append(proxy)

        proxy.notify("init", [0])

    @expose(name="players")
    def _players(self, *args):
        self.ref.reply(list(self.players))

    @expose
    def calc(self, num_clients=1, iterations=10000):
        if len(list(self.players)) < num_clients:
            self.ref.reply("Not enough clients connected")
            return

        answers = []

        for ac_num in range(num_clients):
            player = self.players[ac_num]

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
            res += answer.get()
        self.ref.reply(res)

    @expose
    def minigame(self):
        """Demos a small game."""
        if len(self.players) != 2:
            self.ref.reply("Need two players.")
            return

        reqs = []

        for player in self.players:
            reqs.append( player.query("random_int", []) )

        res = 0
        for answer in reqs:
            res += answer.get()

        if res % 2 != 0:
            self.ref.reply("Player 1 wins")
        else:
            self.ref.reply("Player 2 wins")

remote = RemoteConnection().start_listener("localhost", 50007)
actor_ref = actor_of(ServerActor)
remote.register("main-actor", actor_ref)
remote.start_all()

#incoming_bundler = IncomingConnectionsActor(incoming_connections, inbox)
#incoming_bundler.start()

def printcol(msg):
    """Using a helper function to get coloured output"""
    print(colorama.Fore.BLUE + str(msg) + colorama.Fore.RESET)

class EndSession(Exception):
    pass

import json
try:
    while True:
        inp = input("> ")
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
            print("value error")
            continue

        try:
            if len(params):
                req = actor_ref.query(method, params).get()
            else:
                req = actor_ref.query(method).get()
        except TypeError:
            print("Need to get list")
            continue

#        try:
        print(req)
#        except AttributeError:
#            print req.error

except (KeyboardInterrupt, EndSession):
    print("Interrupted")

    req =  actor_ref.stop()
#    actor.stop()
    remote.stop()
    import sys
    sys.exit()

#remote = remote_start(JsonThreadedListeningServer, "localhost", 9990).register_actor(RemoteActor)

# get with a timeout seems to eat cpu
# (http://blog.codedstructure.net/2011/02/concurrent-queueget-with-timeouts-eats.html)
# maybe we should kill threads using a special input value from top to bottom


