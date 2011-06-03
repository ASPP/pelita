import threading as _threading
import logging

_log = logging.getLogger("threading")
_log.setLevel(logging.DEBUG)
FORMAT = '[%(asctime)-15s][%(levelname)s][%(funcName)s] %(message)s'
logging.basicConfig(format=FORMAT)


class SuspendableThread(_threading.Thread):
    """Base class for a thread which may be suspended."""
    def __init__(self):
        _threading.Thread.__init__(self)
        self._running = False

        # Define a special event which can be flagged to wait.
        self._unpaused = _threading.Event()
        self._unpaused.set()

    def run(self):
        """Executes the thread.
        
        This needs only be overriden, if a special running behaviour is needed.
        In many cases, it is sufficient to override _run().
        """
        while self._running:
            self._unpaused.wait()
            self._run()

        _log.debug("Ended thread %s", self)

    def suspend(self):
        _log.debug("Suspending thread %s", self)
        self._unpaused.clear()

    def resume(self):
        _log.debug("Resuming thread %s", self)
        self._unpaused.set()

    def stop(self):
        _log.debug("Stopping thread %s", self)
        self._running = False

    def start(self):
        _log.debug("Starting thread %s", self)
        self._running = True
        _threading.Thread.start(self)

    def _run(self):
        """This method will be executed in a while loop as long as the thread runs."""
        raise NotImplementedError

class Value(object):
    """Simple wrapper around a value. All access must be done through get, put and do."""
    def __init__(self, value):
        self.value = value
        self.mutex = _threading.Lock()

    def get(self):
        """Return the internal value."""
        # we use the with-statement here to automatically
        # release the lock when we return
        with self.mutex:
            return self.value

    def put(self, value):
        """Set the internal value to value."""
        with self.mutex:
            self.value = value
            return self.value

    def do(self, fun):
        """Execute fun on the value."""
        with self.mutex:
            self.value = fun(self.value)
            return self.value

class Counter(Value):
    def inc(self):
        """Increase self.value by one."""
        with self.mutex:
            self.value += 1
            return self.value


