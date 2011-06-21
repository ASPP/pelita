# -*- coding: utf-8 -*-

import Queue
import socket

import logging
_logger = logging.getLogger("pelita.mailbox")
_logger.setLevel(logging.DEBUG)

from pelita.messaging.utils import SuspendableThread, CloseThread
from pelita.messaging.remote import MessageSocketConnection
from pelita.messaging import StopProcessing, DeadConnection, BaseMessage, Query, Request, RequestDB


class JsonThreadedInbox(SuspendableThread):
    def __init__(self, mailbox, inbox):
        super(JsonThreadedInbox, self).__init__()
        self.mailbox = mailbox
        self.connection = mailbox.connection

        self._queue = inbox

    def _run(self):
        message = self.handle_inbox()

        if isinstance(message, BaseMessage) and message.is_response:

            awaiting_result = self.mailbox._requests.get_request(message.id)
            if awaiting_result is not None:
                awaiting_result._queue.put(message)
                # TODO need to handle race conditions

                return # finish handling of messages here

            else:
                _logger.warning("Received a response (%r) without a waiting future. Dropped response.", message.dict)
                return

        self._queue.put(message)

    def handle_inbox(self):
        try:
            recv = self.connection.read()
        except socket.timeout as e:
            _logger.debug("socket.timeout: %r (%r)" % (e, self))
            return
        except DeadConnection:
            _logger.debug("Remote connection is dead, closing mailbox in %r", self)
            self.mailbox.stop()
            raise CloseThread

        message = recv
        _logger.info("Processing inbox %r", message.dict)
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
        super(JsonThreadedOutbox, self).__init__()
        self.mailbox = mailbox
        self.connection = mailbox.connection

        self._queue = outbox

    def _run(self):
        self.handle_outbox()

    def handle_outbox(self):
        try:
            to_send = self._queue.get(True, 3)

            _logger.info("Processing outbox %r", to_send)
            if to_send is StopProcessing:
                raise CloseThread

            self.connection.send(to_send)
        except Queue.Empty:
            pass

class MailboxConnection(object):
    """A mailbox bundles an incoming and an outgoing connection."""
    def __init__(self, connection, inbox=None, outbox=None):
        self.connection = MessageSocketConnection(connection)

        self.inbox = inbox or Queue.Queue()
        self.outbox = outbox or Queue.Queue()

        self._inbox = JsonThreadedInbox(self, self.inbox)
        self._outbox = JsonThreadedOutbox(self, self.outbox)

        self._requests = RequestDB()

    def start(self):
        _logger.info("Starting mailbox %r", self)
        self._inbox.start()
        self._outbox.start()

    def stop(self):
        _logger.info("Stopping mailbox %r", self)
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
            # Update the message.id
            message.id = self._requests.create_id(message.id)

            req_obj = Request(message.id)
            # save the id to the _requests dict
            self._requests.add_request(req_obj)

            message.mailbox = self

            self.put(message)
            return req_obj
        else:
            raise ValueError