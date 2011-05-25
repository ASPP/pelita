import socket
import json
import threading

import logging

from Queue import Queue

log = logging.getLogger("jsonSocket")
log.setLevel(logging.DEBUG)
FORMAT = '[%(asctime)-15s][%(levelname)s][%(funcName)s] %(message)s'
logging.basicConfig(format=FORMAT)

import weakref

class DeadConnection(Exception):
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
            raise
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


def get_rpc(json):
    classes = [Message, Result, Error]
    for cls in classes:
        try:
            return cls(**json)
        except TypeError:
            pass
    raise ValueError("Wrong keys in JSON: {0}.".format(json))

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


class Value():
    def __init__(self, value):
        self.value = value
        self.mutex = threading.Lock()

    def get(self):
        self.mutex.acquire()
        val = self.value
        self.mutex.release()
        return val

    def put(self, value):
        self.mutex.acquire()
        self.value = value
        self.mutex.release()
        return val

    def do(self, fun):
        self.mutex.acquire()
        self.value = fun(self.value)
        val = self.value
        self.mutex.release()
        return val

class Counter(Value):
    def inc(self):
        self.mutex.acquire()
        self.value += 1
        val = self.value
        self.mutex.release()
        return val

class JsonRPCSocketConnection(JsonSocketConnection):
    """Implements a socket for JSON-RPC communication."""
    def __init__(self, connection):
        super(JsonRPCSocketConnection, self).__init__(connection)
        self._requests = weakref.WeakValueDictionary()
        self._counter = Counter(0)

    def send(self, msg, check=True):
        try:
            get_rpc(msg)
        except ValueError:
            if check==True:
                raise
            else:
                pass

        super(JsonRPCSocketConnection, self).send(msg)

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
        obj = Message("msg", 0).rpc # super(JsonRPCSocketConnection, self).read()
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

class JsonThreadedSocketConnection(threading.Thread, JsonRPCSocketConnection):
    def __init__(self, connection):
        threading.Thread.__init__(self)
        JsonRPCSocketConnection.__init__(self, connection)

#        self.connection.settimeout(3)
        self.connection.setblocking(1)
        self._running = False

    def run(self):
        while self._running:
            try:
                print "read"
                obj = self.read()
                print obj
            except socket.timeout as e:
                log.debug("socket.timeout: %s" % e)
                continue
            except DeadConnection:
                self.close()
                self._running = False
            except Exception as e:
                log.exception(e)
                continue

        log.info("End socket connection server.")

    def start(self):
        log.info("Start socket connection server.")
        self._running = True
        threading.Thread.start(self)

    def stop(self):
        self._running = False

class SuspendableThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self._running = False
        self._unpaused = threading.Event()
        self._unpaused.set()

    def run(self):
        if self._running:
            log.info("Thread runs %s", self)
            self._unpaused.wait()
            self._run()

        log.info("Ended thread %s", self)

    def suspend(self):
        log.info("Suspending thread %s", self)
        self._unpaused.clear()

    def resume(self):
        log.info("Resuming thread %s", self)
        self._unpaused.set()

    def stop(self):
        log.info("Stopping thread %s", self)
        self._running = False

    def start(self):
        log.info("Starting thread %s", self)
        self._running = True
        threading.Thread.start(self)

    def _run(self):
        raise NotImplementedError


class JsonThreadedInbox(SuspendableThread):
    def __init__(self, connection, inbox=None):
        SuspendableThread.__init__(self)
        self.connection = connection

        self._queue = inbox or Queue()

    def _run(self):
        self.handle_inbox()

    def handle_inbox(self):
        recv = self.connection.read()
        self._queue.put( (self.connection.connection, recv) )


class JsonThreadedOutbox(SuspendableThread):
    def __init__(self, connection, outbox=None):
        SuspendableThread.__init__(self)
        self.connection = connection

        self._queue = outbox or Queue()

    def _run(self):
        self.handle_outbox()

    def handle_outbox(self):
        to_send = self._queue.get()
        log.info("Processing outbox %s", to_send)
        self.connection.send(to_send)

class MailboxConnection(object):
    def __init__(self, connection, inbox=None, outbox=None):
        connection = JsonRPCSocketConnection(connection)

        self._inbox = JsonThreadedInbox(connection, inbox)
        self._outbox = JsonThreadedOutbox(connection, outbox)

    def start(self):
        self._inbox.start()
        self._outbox.start()

    def stop(self):
        self._inbox.stop()
        self._outbox.stop()

    def put(self, msg, block=True, timeout=None):
        self._outbox._queue.put(msg, block, timeout)

    def get(self, block=True, timeout=None):
        return self._inbox._queue.get(block, timeout)

