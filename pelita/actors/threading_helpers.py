import threading as _threading
import logging

log = logging.getLogger("threading")
log.setLevel(logging.INFO)
FORMAT = '[%(asctime)-15s][%(levelname)s][%(funcName)s] %(message)s'
logging.basicConfig(format=FORMAT)


class SuspendableThread(_threading.Thread):
    def __init__(self):
        _threading.Thread.__init__(self)
        self._running = False
        self._unpaused = _threading.Event()
        self._unpaused.set()

    def run(self):
        while self._running:
            self._unpaused.wait()
            self._run()

        log.debug("Ended thread %s", self)

    def suspend(self):
        log.debug("Suspending thread %s", self)
        self._unpaused.clear()

    def resume(self):
        log.debug("Resuming thread %s", self)
        self._unpaused.set()

    def stop(self):
        log.debug("Stopping thread %s", self)
        self._running = False

    def start(self):
        log.debug("Starting thread %s", self)
        self._running = True
        _threading.Thread.start(self)

    def _run(self):
        raise NotImplementedError

class Value(object):
    def __init__(self, value):
        self.value = value
        self.mutex = _threading.Lock()

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


