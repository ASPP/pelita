# -*- coding: utf-8 -*-

import Queue
import weakref
import socket

import logging
_logger = logging.getLogger("pelita.mailbox")
_logger.setLevel(logging.DEBUG)

from pelita.utils import SuspendableThread, Counter, CloseThread
from pelita.remote.jsonconnection import JsonRPCSocketConnection
from pelita.actors import StopProcessing, DeadConnection, Response, Query, Request


class JsonThreadedInbox(SuspendableThread):
    def __init__(self, mailbox, inbox):
        SuspendableThread.__init__(self)
        self.mailbox = mailbox
        self.connection = mailbox.connection

        self._queue = inbox

    def _run(self):
        message = self.handle_inbox()

        if isinstance(message, Response):

            awaiting_result = self.mailbox._requests.get(message.id, None)
            if awaiting_result is not None:
                awaiting_result._queue.put(message)
                # TODO need to handle race conditions

                return # finish handling of messages here

            else:
                _logger.warning("Received a response (%s) without a waiting future. Dropped response.", message.rpc)
                return

        self._queue.put(message)

    def handle_inbox(self):
        try:
            recv = self.connection.read()
        except socket.timeout as e:
            _logger.debug("socket.timeout: %s (%s)" % (e, self))
            return
        except DeadConnection:
            _logger.debug("Remote connection is dead, closing mailbox in %s", self)
            self.mailbox.stop()
            raise CloseThread

        message = recv
        _logger.info("Processing inbox %s", message.rpc)
        # add the mailbox to the message
        message.mailbox = self.mailbox
        return message

# TODO Not in use now, we rely on timeout until we know better
#    def stop(self):
#        SuspendableThread.stop(self)
#
#        self.connection.connection.shutdown(socket.SHUT_RDWR)
#        self.connection.close()



class JsonThreadedOutbox(SuspendableThread):
    def __init__(self, mailbox, outbox):
        SuspendableThread.__init__(self)
        self.mailbox = mailbox
        self.connection = mailbox.connection

        self._queue = outbox

    def _run(self):
        self.handle_outbox()

    def handle_outbox(self):
        try:
            to_send = self._queue.get(True, 3)

            _logger.info("Processing outbox %s", to_send)
            if to_send is StopProcessing:
                raise CloseThread

            self.connection.send(to_send)
        except Queue.Empty:
            pass

class MailboxConnection(object):
    """A mailbox bundles an incoming and an outgoing connection."""
    def __init__(self, connection, inbox=None, outbox=None):
        self.connection = JsonRPCSocketConnection(connection)

        self.inbox = inbox or Queue.Queue()
        self.outbox = outbox or Queue.Queue()

        self._inbox = JsonThreadedInbox(self, self.inbox)
        self._outbox = JsonThreadedOutbox(self, self.outbox)

        self._requests = weakref.WeakValueDictionary()
        self._counter = Counter(0)

    def start(self):
        _logger.info("Starting mailbox %s", self)
        self._inbox.start()
        self._outbox.start()

    def stop(self):
        _logger.info("Stopping mailbox %s", self)
        self.inbox.put(StopProcessing)
        self.outbox.put(StopProcessing) # I need to to this or the thread will not stop...
        self._inbox.stop()
        self._outbox.stop()
        self.connection.close()

    def put(self, message, block=True, timeout=None):
        self.outbox.put(message, block, timeout)

    def get(self, block=True, timeout=None):
        return self.inbox.get(block, timeout)

    def request(self, message):
        """Put a query into the outbox and return the Request object."""
        if isinstance(message, Query):
            # save the id to the _requests dict
            if message.id is None:
                message.id = self._counter.inc()
            else:
                _logger.info("Using existing id.")

            req_obj = Request(message.id)
            self._requests[message.id] = req_obj

            self.put(message)
            return req_obj
        else:
            raise ValueError

