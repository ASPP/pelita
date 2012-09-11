# -*- coding: utf-8 -*-

from pelita.messaging import Actor, DispatchingActor, expose, actor_of, RemoteConnection

import logging

_logger = logging.getLogger("clientActor")
_logger.setLevel(logging.DEBUG)

from pelita.utils.colorama_wrapper import colorama

FORMAT = '[%(asctime)s,%(msecs)03d][%(name)s][%(levelname)s][%(funcName)s]' + colorama.Fore.MAGENTA + ' %(message)s' + colorama.Fore.RESET
logging.basicConfig(format=FORMAT, datefmt="%H:%M:%S")

from pelita.utils import ThreadInfoLogger
ThreadInfoLogger(10).start()

def init(*params):
    print(params)

def calculate_pi_for(start, number_of_elems):
    acc = 0.0
    for i in range(start, start + number_of_elems):
        acc += 4.0 * (1 - (i % 2) * 2) / (2 * i + 1)
    return acc

import math
def slow_series(start, number_of_elems):
    acc = 0.0
    for i in range(start, start + number_of_elems):
        acc += 1.0 / (i * (math.log(i)*math.log(i)))
    return acc

class ClientActor(DispatchingActor):
    @expose
    def init(self, *params):
        init(*params)

    @expose
    def statechanged(self):
        self.ref.reply("NORTH")

    @expose
    def calculate_pi_for(self, *params):
        res = calculate_pi_for(*params)
        self.ref.reply(res)

    @expose
    def slow_series(self, *params):
        res = slow_series(*params)
        self.ref.reply(res)

    @expose
    def random_int(self):
        import random
        self.ref.reply(random.randint(0, 10))

actor = actor_of(ClientActor)
actor.start()

port = 50007

remote_actor = RemoteConnection().actor_for("main-actor", "localhost", port)

res = remote_actor.query("multiply", [1, 2, 3, 4])
print(res.get())

remote_actor.notify("hello", [str(actor.uuid)])

try:
    while actor.is_alive:
        actor.join(1)

except KeyboardInterrupt:
    print("Interrupted")
    actor.stop()


