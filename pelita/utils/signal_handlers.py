# -*- coding: utf-8 -*-

""" Signal handlers.
"""

import os
import signal

def exit_handler(*args):
    """ Simple handler to just quit using os._exit(-1).

    This is not a very graceful approach. None of the resources that the program
    acquired during its lifecycle will be released. This may or may not affect
    network resources, open files, allocated memory, and possibly even child
    processes.

    """
    os._exit(-1)

# TODO handler should use logging

def keyboard_interrupt_handler(signo, frame):
    print "Got SIGINT. Exit!"
    exit_handler()

signal.signal(signal.SIGINT, keyboard_interrupt_handler)

# is added  pelita/ui/tk_canvas:TkApplication
def wm_delete_window_handler():
    print "WM_DELETE_WINDOW. Exit!"
    exit_handler()


