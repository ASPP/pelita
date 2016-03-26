""" Signal handlers.
"""

import logging
import os
import platform
import signal
import sys

# make a logger for these handlers that prints info messages to stderr
_logger = logging.getLogger("signal_handlers")
_logger.setLevel(logging.INFO)
_logger.addHandler(logging.StreamHandler(sys.stderr))

def exit_handler(*args):
    """ Simple handler to just quit using os._exit(-1).

    This is not a very graceful approach. None of the resources that the program
    acquired during its lifecycle will be released. This may or may not affect
    network resources, open files, allocated memory, and possibly even child
    processes.

    """
    # defensively shutdown the logging system
    logging.shutdown()
    # kill all processes in processgroup.
    # we need this in case we use the multiprocessing.
    if platform.system() == 'Windows':
        import win32api, win32con
        handle = win32api.OpenProcess(win32con.PROCESS_TERMINATE,
                                      0, os.getpid())
        win32api.TerminateProcess( handle, 0 )
        win32api.CloseHandle( handle )
    else:
        os.kill(os.getpid(), signal.SIGTERM)

def keyboard_interrupt_handler(signo, frame):
    _logger.info("Got SIGINT. Exit!")
    exit_handler()

# is added  pelita/ui/tk_canvas:TkApplication
def wm_delete_window_handler():
    _logger.info("Got WM_DELETE_WINDOW. Exit!")
    exit_handler()
