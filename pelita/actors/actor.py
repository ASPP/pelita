import Queue

import logging
import weakref

from pelita.actors import SuspendableThread, Counter

from pelita.remote.jsonconnection import Response

log = logging.getLogger("jsonSocket")
log.setLevel(logging.DEBUG)
FORMAT = '[%(asctime)-15s][%(levelname)s][%(funcName)s] %(message)s'
logging.basicConfig(format=FORMAT)


class Request(object):
    def __init__(self, id):
        self.id = id
        self._queue = Queue.Queue(maxsize=1)

    def get(self, block=True, timeout=None):
        return self._queue.get(block, timeout)

    def get_or_none(self):
        """Returns the result or None, if the value is not available."""
        try:
            return self._queue.get(False).result
        except Queue.Empty:
            return None

    def has_result(self):
        """Checks whether a result is available.
        
        This method does not guarantee that a subsequent call of Request.get() will succeed.
        However, unless there is code which calls get() in the background, this method
        should be save to use.
        """
        return self._queue.full()

class RemoteActor(SuspendableThread):
    def __init__(self, inbox):
        SuspendableThread.__init__(self)
        self._inbox = inbox

        self._requests = weakref.WeakValueDictionary()
        self._counter = Counter(0)

    def _run(self):
        try:
            sender, msg = self._inbox.get(True, 3)
        except Queue.Empty:
            return

        if isinstance(msg, Response):
            awaiting_result = self._requests.get(msg.id, None)
            if awaiting_result is not None:
                awaiting_result._queue.put(msg)
                # TODO need to handle race conditions

                return # finish handling of messages here

            else:
                log.warning("Received a response (%s) without a waiting future. Dropped response.", msg)
                return

        # default
        self.receive(sender, msg)


    def request(self, sender, msg):
        """Requests an answer and returns a Request object."""

        if getattr(msg, "id", None) is None:
            id = self._counter.inc()
            msg.id = id
        else:
            log.info("Using existing id.")

        req_obj = Request(id)
        self._requests[id] = req_obj

        # send as json
        self.send(sender, msg)

        return req_obj

    def receive(self, sender, msg):
        log.debug("Received sender %s msg %s", sender, msg)

    def send(self, sender, msg):
        sender.put(msg)


class ProxyActor(object):
    def __init__(self, actor):
        self._actor = actor

    def query(self, remote, method, params):
        self._actor.request(remote, Query(method, params, None))



