# -*- coding: utf-8 -*-

"""Various helper methods."""
import threading
import logging

from pelita.utils import SuspendableThread

_logger = logging.getLogger("pelita.utils")
_logger.setLevel(logging.DEBUG)

__docformat__ = "restructuredtext"


class ThreadInfoLogger(SuspendableThread):
    def __init__(self, interval, show_threads=True):
        super(ThreadInfoLogger, self).__init__()
        self.lvl = logging.DEBUG
        self.interval = interval
        self.show_threads = show_threads

        self.thread.daemon = True
        self._wait = threading.Event()

    def _run(self):
        self._wait.wait(self.interval)
        _logger.log(self.lvl, "%d threads alive (including this logger)" % threading.active_count())
        if self.show_threads:
            _logger.log(self.lvl, ", ".join(str(t) for t in threading.enumerate()))


