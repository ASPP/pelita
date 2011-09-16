# -*- coding: utf-8 -*-

import Queue
import copy
import Tkinter

import logging

from pelita.viewer import AbstractViewer
from pelita.ui.tk_canvas import TkApplication

_logger = logging.getLogger("pelita.tk_viewer")
_logger.setLevel(logging.DEBUG)

class TkViewer(AbstractViewer):
    """ Initialises Tk based viewer for the game.

    The viewer may be passed to a GameMaster instance by calling::

        viewer = TkViever()
        gm.register_viewer(viewer)

    Afterwards, Tk needs to run in the main thread, which is done
    by calling::

        viewer.app.mainloop()

    Notes
    -----
    Any Tk application must run in the main thread. Therefore,
    the real game needs to run in some background thread. This means
    that we’ll need to exchange all information about current universe
    states in a thread-safe way.
    A good way to accomplish this is using a simple Queue.

    There is however a problem with a simple Queue approach: The producer
    (ie. the GameMaster) may produce new states much faster than the
    consumer is able to process them. (ie. the Viewer might show some
    animations which just take their time.)
    A queue which is just naïvely filled might therefore be a suboptimal
    solution when the game is finished long before the animations.

    One solution is to use a Queue with a maximum size. If the Queue is
    filled, no producer may put any more items into it until another
    item is consumed.

    By default, the TkViewer queue is set to a maximum size of 1 to
    get the least possible delay between game state and animation.

    If Tk crashes, however, this may lead to dead locks, so we must
    add a timeout parameter, if the animation takes too long.
    The respective states and events will be lost then.

    Parameters
    ----------
    queue_size : int, default = 1
        The maximum size of the exchange queue between
        gm.observe and the Tk viewer
    timeout : The maximum time to wait before we give up
        observing a new state (or None for no timeout)
    geometry: tuple, default = None
        The size (in pixel) of the game root window. None means
        using a bit less than the screen size.

    Attributes
    ----------
    observe_queue :  The exchange queue
    app : The TkApplication class

    """
    def __init__(self, queue_size=1, geometry=None, timeout=0.5):
        self.observe_queue = Queue.Queue(maxsize=queue_size)

        self.root = Tkinter.Tk()
        if geometry is None:
            root_geometry = '900x510'
        else:
            root_geometry = str(geometry[0])+'x'+str(geometry[1])
        # put the root window in some sensible position
        self.root.geometry(root_geometry+'+40+40')
        
        self.app = TkApplication(queue=self.observe_queue,
                                 geometry = geometry,
                                 master=self.root)
        self.root.after_idle(self.app.read_queue)

        self.timeout = timeout
        if self.timeout == 0:
            self.block = False
        else:
            self.block = True

    def _put(self, obj):
        try:
            self.observe_queue.put(obj, self.block, self.timeout)
        except Queue.Full:
            _logger.info("Queue is filled. Skipping.")
            pass

    def set_initial(self, universe):
        self._put(copy.deepcopy({
            "universe": universe,
        }))

    def observe(self, round_, turn, universe, events):
#        print "observed", events

        self._put(copy.deepcopy({
            "round": round_,
            "turn": turn,
            "universe": universe,
            "events": events}))

