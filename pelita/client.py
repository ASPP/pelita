# -*- coding: utf-8 -*-

from actors.actor import Actor


class Client(object):
    server = Actor.remote.actorFor("chat:service", "localhost", 9990)


