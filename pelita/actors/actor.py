import Queue

import logging
import weakref

from pelita.actors import SuspendableThread

log = logging.getLogger("jsonSocket")
log.setLevel(logging.DEBUG)
FORMAT = '[%(asctime)-15s][%(levelname)s][%(funcName)s] %(message)s'
logging.basicConfig(format=FORMAT)


class RemoteActor(SuspendableThread):
    def __init__(self, inbox):
        SuspendableThread.__init__(self)
        self._inbox = inbox

        self._reply_queues = weakref.WeakValueDictionary()

    def _run(self):
        try:
            sender, msg = self._inbox.get(True, 3)
            try:
                awaiting_result = self._reply_queues[msg.id]
                awaiting_result._queue.put(msg)
            except KeyError:
                self.receive(sender, msg)
        except Queue.Empty:
            pass

    def receive(self, sender, msg):
        log.debug("Received sender %s msg %s", sender, msg)

    def send(self, sender, msg):
        sender.put(msg)

    def register_result(self, id, result):
        self._reply_queues[id] = result

class Result(object):
    def __init__(self):
        self._queue = Queue()

    def get(self, blocking=True, timeout=None):
        return self._queue.get(blocking, timeout)

class ProxyActor(object):
    def __init__(self, actor):
        self._actor = actor

    def query(self, remote, method, params):
        result = Result()
        msg = Message(method, params, id(result))
        self._actor.register_result(msg.id, result)
#        self._actor
        return result



