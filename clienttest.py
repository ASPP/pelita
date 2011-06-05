# -*- coding: utf-8 -*-

from pelita.remote import TcpConnectingClient
from pelita.remote.jsonconnection import MailboxConnection

from pelita.actors import RemoteActor
from pelita.actors import Message, Query, Error

import logging

_logger = logging.getLogger("clientActor")
_logger.setLevel(logging.DEBUG)
FORMAT = '[%(asctime)-15s][%(levelname)s][%(funcName)s] %(message)s'
logging.basicConfig(format=FORMAT)

from pelita.utils import ThreadInfoLogger
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

class ClientActor(RemoteActor):
    def receive(self, message):
        if message.method == "init":
            reply = init(*message.params)

        elif message.method == "statechanged":
            sender.put(message.reply("NORTH"))

        elif message.method == "calculate_pi_for":
            res = calculate_pi_for(*message.params)
            message.reply(res)

        elif message.method == "slow_series":
            res = slow_series(*message.params)
            message.reply(res)
        else:
            try:
                message.reply_error("Message not found")
            except AttributeError:
                _logger.warning("Message not found.")

sock = TcpConnectingClient(host="", port=50007)
conn = sock.handle_connect()

remote = MailboxConnection(conn)
remote.start()

actor = ClientActor(remote.inbox)
actor.start()

actor.send(remote, Message("hello", "Im there"))


import time
try:
    while 1:
        time.sleep(10)
except KeyboardInterrupt:
    print "Interrupted"
    actor.stop()
    remote.stop()


