# -*- coding: utf-8 -*-

from pelita.messaging.remote import TcpConnectingClient
from pelita.messaging.mailbox import MailboxConnection

from pelita.messaging import Actor, RemoteActorProxy, DispatchingActor, dispatch

import logging

_logger = logging.getLogger("clientActor")
_logger.setLevel(logging.DEBUG)
FORMAT = '[%(asctime)s,%(msecs)03d][%(name)s][%(levelname)s][%(funcName)s] %(message)s'
logging.basicConfig(format=FORMAT, datefmt="%H:%M:%S")

from pelita.messaging.utils import ThreadInfoLogger
ThreadInfoLogger(10).start()

def init(*params):
    print params

def calculate_pi_for(start, number_of_elems):
    acc = 0.0
    for i in xrange(start, start + number_of_elems):
        acc += 4.0 * (1 - (i % 2) * 2) / (2 * i + 1)
    return acc

import math
def slow_series(start, number_of_elems):
    acc = 0.0
    for i in xrange(start, start + number_of_elems):
        acc += 1.0 / (i * (math.log(i)*math.log(i)))
    return acc

class ClientActor(DispatchingActor):
    @dispatch
    def init(self, message, *params):
        init(*params)

    @dispatch
    def statechanged(self, message):
        message.reply("NORTH")

    @dispatch
    def calculate_pi_for(self, message, *params):
        res = calculate_pi_for(*params)
        message.reply(res)

    @dispatch
    def slow_series(self, message, *params):
        res = slow_series(*params)
        message.reply(res)

    @dispatch
    def random_int(self, message):
        import random
        message.reply(random.randint(0, 10))

sock = TcpConnectingClient(host="", port=50007)
conn = sock.handle_connect()

actor = ClientActor()
actor.start()

remote = MailboxConnection(conn, actor)
remote.start()

remote_actor = RemoteActorProxy(remote)
remote_actor.notify("hello", "Im there")

try:
    while actor.thread.is_alive():
        actor.thread.join(1)
except KeyboardInterrupt:
    print "Interrupted"
    actor.stop()
    remote.stop()


