# -*- coding: utf-8 -*-

import Queue

import logging
from pelita.utils import SuspendableThread, Counter, CloseThread
from pelita.actors import Query

_logger = logging.getLogger("pelita.actor")
_logger.setLevel(logging.DEBUG)


class DeadConnection(Exception):
    """Raised when the connection is lost."""

class StopProcessing(object):
    """If a thread encounters this value in a queue, it is advised to stop processing."""


class Actor(SuspendableThread):
    def __init__(self, inbox):
        SuspendableThread.__init__(self)
        self._inbox = inbox

    def _run(self):
        try:
            message = self._inbox.get(True, 3)
        except Queue.Empty:
            return

        if message is StopProcessing:
            raise CloseThread()

        # default
        self.receive(message)

    def request(self, sender, method, params, id=None):
        """Requests an answer and returns a Request object."""
        query = Query(method, params, id)

        # send as json
        return sender.request(query)

    def receive(self, message):
        _logger.debug("Received message %s.", message)

    def send(self, sender, message):
        sender.put(message)


class ProxyActor(object):
    def __init__(self, actor):
        self._actor = actor

    def query(self, remote, method, params):
        self._actor.request(remote, Query(method, params, None))



