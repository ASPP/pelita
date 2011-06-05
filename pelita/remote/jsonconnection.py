# -*- coding: utf-8 -*-

import socket
import json

import logging

from Queue import Queue, Empty

from pelita.actors import SuspendableThread, get_rpc, rpc_instances, Error, CloseThread, StopProcessing, DeadConnection

_logger = logging.getLogger("pelita.jsonSocket")
_logger.setLevel(logging.DEBUG)

import weakref

import traceback


class JsonSocketConnection(object):
    """Implements a socket for JSON communication."""
    def __init__(self, connection):
        self.connection = connection

        # Our terminator must never be included in our JSON strings
        # also, it must be a one-byte character for easier parsing
        self._terminator = "\x04" # End of transmission

        self.buffer = []
        self.incoming = ""

    @property
    def terminator(self):
        return self._terminator

    @terminator.setter
    def terminator(self, value):
        if len(value) != 1:
            raise RuntimeError("Terminator length must be 1.")
        self._terminator = value

    def send(self, obj):
        if self.connection:
            json_string = json.dumps(obj)
            self._send(json_string)
        else:
            raise RuntimeError("Cannot send without a connection.")

    def _send(self, json_string):
        if self.terminator in json_string:
            raise RuntimeError("JSON contains invalid termination character.")

        data = json_string + self.terminator

        sent_bytes = 0
        while sent_bytes < len(data):
            _logger.info("Sending raw data %s", data[sent_bytes:])
            sent_bytes += self.connection.send(data[sent_bytes:])

    def _read(self):
        try:
            data = self.connection.recv(4096)
            _logger.info("Got raw data %s", data)
        except socket.error as e:
            _logger.warning("Caught an error in recv")
            _logger.warning(e)
            # Waiting a bit
            import time
            time.sleep(1)
            return
            data = ""

        if not data:
            # this connection seems to be dead
            raise DeadConnection()

        split_data = data.split(self.terminator)
        # we split the data to get the following:
        # [contd*, full*, incomplete]

        # the last part is always incomplete or empty
        incomplete = split_data[-1]
        complete = split_data[:-1]

        if complete:
            # the first element of complete is the continued
            # incoming object of the last _read
            contd = complete.pop(0)
            self.incoming += contd
            self.buffer.append(self.incoming)
            self.incoming = ""

        if complete:
            # if there is still something left in complete,
            # move everything to the buffer
            self.buffer += complete
            # we throw away complete to make clear we have
            # collected all data
            complete = []

        # append the incomplete data to the incoming string
        self.incoming += incomplete

    def read(self):
        # collect data until there is an object in buffer
        print "TRYING TO READ"
        while not self.buffer:
            print "READ"
            self._read()

        # get the first elemet
        data = self.buffer.pop(0)
        json_data = json.loads(data)
        _logger.debug("Data read %s", json_data)
        return json_data

    def close(self):
        self.connection.close()


class JsonRPCSocketConnection(JsonSocketConnection):
    """Implements a socket for JSON-RPC communication."""
    def __init__(self, connection):
        super(JsonRPCSocketConnection, self).__init__(connection)

    def send(self, rpc_obj):
        if rpc_obj.__class__ in rpc_instances:
            super(JsonRPCSocketConnection, self).send(rpc_obj.rpc)
        else:
            raise ValueError("Message %s is no rpc object." % rpc_obj)

    def read(self):
        obj = super(JsonRPCSocketConnection, self).read()
        _logger.debug("Received: %s", obj)
        try:
            msg_obj = get_rpc(obj)
        except ValueError:
            msg_obj = Error("wrong input", None)

        return msg_obj

class JsonThreadedInbox(SuspendableThread):
    def __init__(self, mailbox, inbox=None):
        SuspendableThread.__init__(self)
        self.mailbox = mailbox
        self.connection = mailbox.connection

        self._queue = inbox

    def _run(self):
        self.handle_inbox()

    def handle_inbox(self):
        try:
            recv = self.connection.read()
        except socket.timeout as e:
            _logger.debug("socket.timeout: %s (%s)" % (e, self))
            return
        except DeadConnection:
            _logger.debug("Remote connection is dead, closing mailbox in %s", self)
            self._queue.put(StopProcessing)
            self.mailbox.stop()
            raise CloseThread

        message = recv
        # add the mailbox to the message
        message.mailbox = self.mailbox
        self._queue.put(message)


class JsonThreadedOutbox(SuspendableThread):
    def __init__(self, mailbox, outbox=None):
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
        except Empty:
            print "Nothing received, going on."
            pass

class MailboxConnection(object):
    def __init__(self, connection, inbox=None, outbox=None):
        self.connection = JsonRPCSocketConnection(connection)

        self.inbox = inbox or Queue()
        self.outbox = outbox or Queue()

        self._inbox = JsonThreadedInbox(self, self.inbox)
        self._outbox = JsonThreadedOutbox(self, self.outbox)

    def start(self):
        _logger.warning("Starting mailbox %s", self)
        self._inbox.start()
        self._outbox.start()

    def stop(self):
        _logger.warning("Stopping mailbox %s", self)
        self._inbox.stop()
        self.outbox.put(StopProcessing) # I need to to this or the thread will not stop...
        self._outbox.stop()

    def put(self, msg, block=True, timeout=None):
        self.outbox.put(msg, block, timeout)

    def get(self, block=True, timeout=None):
        return self.inbox.get(block, timeout)

