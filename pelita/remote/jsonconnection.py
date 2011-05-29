import socket
import json

import logging

from Queue import Queue, Empty

from pelita.actors import SuspendableThread, Counter

log = logging.getLogger("jsonSocket")
log.setLevel(logging.DEBUG)
FORMAT = '[%(asctime)-15s][%(levelname)s][%(funcName)s] %(message)s'
logging.basicConfig(format=FORMAT)

import weakref

import traceback


class DeadConnection(Exception):
    """Raised when the connection is lost."""
    pass

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
            log.info("Sending raw data %s", data[sent_bytes:])
            sent_bytes += self.connection.send(data[sent_bytes:])

    def _read(self):
        try:
            data = self.connection.recv(4096)
            log.info("Got raw data %s", data)
        except socket.error:
            log.warning("Caught an error in recv")
            raise DeadConnection()
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
        while not self.buffer:
            self._read()

        # get the first elemet
        data = self.buffer.pop(0)
        json_data = json.loads(data)
        log.debug("Data read %s", json_data)
        return json_data

    def close(self):
        self.connection.close()


class Message(object):
    def __init__(self, method, params, id=None):
        self.method = method
        self.params = params
        self.id = id

    @property
    def rpc(self):
        return {"method": self.method, "params": self.params, "id": self.id}

class Result(object):
    def __init__(self, result, id):
        self.result = result
        self.id = id

    @property
    def rpc(self):
        return {"result": self.result, "id": self.id}

class Error(object):
    def __init__(self, error, id):
        self.error = error
        self.id = id

    @property
    def rpc(self):
        return {"error": self.error, "id": self.id}

class Request(object):
    def __init__(self, id):
        self.id = id
        self._queue = Queue()

    def get(self, timeout=0):
        return self._queue.get(True)# , timeout)


rpc_instances = [Message, Result, Error]

def get_rpc(json):
    for cls in rpc_instances:
        try:
            return cls(**json)
        except TypeError:
            pass
    raise ValueError("Cannot convert JSON {0} to RPC object.".format(json))


class JsonRPCSocketConnection(JsonSocketConnection):
    """Implements a socket for JSON-RPC communication."""
    def __init__(self, connection):
        super(JsonRPCSocketConnection, self).__init__(connection)
        self._requests = weakref.WeakValueDictionary()
        self._counter = Counter(0)

    def send(self, rpc_obj, check=True):
        if rpc_obj in 

        super(JsonRPCSocketConnection, self).send(msg.rpc_obj)

    def request(self, msg):
        """Requests an answer and returns a Request object."""

        id = self._counter.inc()

        # compile message
        msg_obj = Message("msg", msg, id)
        # send as json
        self.send(msg_obj.rpc)

        req_obj = Request(id)
        self._requests[id] = req_obj
        return req_obj

    def read(self):
        obj = super(JsonRPCSocketConnection, self).read()
        log.debug("Received: %s", obj)
        try:
            msg_obj = get_rpc(obj)
        except ValueError:
            msg_obj = Error("wrong input", None)
        return msg_obj
        self.id += 1
        try:
            self._requests[self.id]._queue.put(json_data.toupper())
            log.debug("Adding id to queue.")
        except KeyError:
            pass

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
            log.debug("socket.timeout: %s (%s)" % (e, self))
            return
        except DeadConnection:
            log.debug("Remote connection is dead, closing mailbox in %s", self)
            self.mailbox.stop()
            self._running = False
            return
        self._queue.put( (self.mailbox, recv) )


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

            if to_send is None:
                self.stop()
                return

#        log.info("Processing outbox %s", to_send)
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
        log.warning("Starting mailbox %s", self)
        self._inbox.start()
        self._outbox.start()

    def stop(self):
        log.warning("Stopping mailbox %s", self)
        self._inbox.stop()
        self.outbox.put(None) # I need to to this or the thread will not stop...
        self._outbox.stop()

    def put(self, msg, block=True, timeout=None):
        self._outbox._queue.put(msg, block, timeout)

    def get(self, block=True, timeout=None):
        return self._inbox._queue.get(block, timeout)

