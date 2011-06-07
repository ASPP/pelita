# -*- coding: utf-8 -*-

import Queue

import logging
from pelita.utils import SuspendableThread, Counter, CloseThread
from pelita.actors import Query, Message

_logger = logging.getLogger("pelita.actor")
_logger.setLevel(logging.DEBUG)


class DeadConnection(Exception):
    """Raised when the connection is lost."""

class StopProcessing(object):
    """If a thread encounters this value in a queue, it is advised to stop processing."""

class AbstractActor(object):
    def request(self, method, params, id=None):
        raise NotImplementedError

    def request_timeout(self, method, params, id=None, timeout=None):
        return self.request(method, params, id).get(True, timeout)

    def send(self, method, params=None):
        raise NotImplementedError

class RemoteActor(AbstractActor):
    def __init__(self, mailbox):
        self.mailbox = mailbox

    def request(self, method, params, id=None):
        """Requests an answer and returns a Request object."""
        query = Query(method, params, id)

        # send as json
        return self.mailbox.request(query)

    def send(self, method, params=None):
        message = Message(method, params)
        self.mailbox.put(message)

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


# TODO implement ActorFutures for Non-Remote actors
#    def request(self, sender, method, params, id=None)
#        """Requests an answer and returns a Request object."""
#        query = Query(method, params, id)
#
#        # send as json
#        return sender.request(query)

    def receive(self, message):
        _logger.debug("Received message %s.", message)

    def send(self, method, params=None):
        message = Message(method, params)
        self._inbox.put(message)


class ProxyActor(object):
    def __init__(self, actor):
        self._actor = actor

    def query(self, remote, method, params):
        self._actor.request(remote, Query(method, params, None))



