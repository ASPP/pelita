# -*- coding: utf-8 -*-

import traceback
import threading as _threading
import logging

_logger = logging.getLogger("pelita.threading")
#_logger.setLevel(logging.DEBUG)

__docformat__ = "restructuredtext"


class CloseThread(Exception):
    """May be raised from inside the _run method to close the thread."""

class SuspendableThread(object):
    """Base class for a thread which may be suspended."""
    def __init__(self):
        # get a (unique?) name for the thread
        # we add the class name, so we know who started the thread
        self._thread = _threading.Thread(target=self.run, name=_newname(self.__class__))
        self._running = False

        # Define a special event which can be flagged to wait.
        self._unsuspended = _threading.Event()
        self._unsuspended.set()

    def run(self):
        """Executes the thread.

        This needs only be overridden, if a special running behaviour is needed.
        In many cases, it is sufficient to override _run().
        """
        while self._running:
            self._unsuspended.wait()
            try:
                self._run()
            except CloseThread:
                self.stop()
            except Exception as e:
                _logger.error("Unhandled exception %r in thread %r. Stopping.", e, self)
                # print exception to stderr
                traceback.print_exc()
                self.stop()

        _logger.debug("Ended thread %r", self)

    @property
    def thread(self):
        return self._thread

    @property
    def paused(self):
        return not self._unsuspended.is_set()

    @paused.setter
    def paused(self, value):
        if value:
            _logger.debug("Suspending thread %r", self)
            self._unsuspended.clear()
        else:
            _logger.debug("Resuming thread %r", self)
            self._unsuspended.set()

    def stop(self):
        _logger.debug("Stopping thread %r", self)
        self._running = False

    def start(self):
        _logger.debug("Starting thread %r", self)
        self._running = True
        self._thread.start()

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

# Helper to generate new thread names
_counter = Counter(0)
def _newname(cls, template="Thread-%s-%d"):
    value = _counter.inc()
    return template % (cls.__name__, value)
