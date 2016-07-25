import logging
import os
import shutil
import sys

import tkinter

from .tk_canvas import TkApplication

_logger = logging.getLogger("pelita.tk_viewer")
_logger.setLevel(logging.DEBUG)

def force_frontmost():
    """ This hack was discussed in https://github.com/ASPP/pelita/issues/345
    and uses Apple Script to tell OS X’s System Events to put a certain
    process in the foreground, focused and at the top position in the
    application stack. (I.e. cmd+tab behaves as expected.)
    """
    if sys.platform == 'darwin' and shutil.which('/usr/bin/osascript'):
        script = 'tell application "System Events" \
                  to set frontmost of the first process whose unix id is {pid} to true'.format(pid=os.getpid())
        os.system("/usr/bin/osascript -e '{script}'".format(script=script))


class TkViewer:
    """ Initialises Tk based viewer for the game.

    The viewer may be passed to a GameMaster instance by calling::

        viewer = TkViever(zmq_address)
        gm.register_viewer(viewer)

    Afterwards, Tk needs to run in the main thread, which is done
    by calling::

        viewer.run()

    Notes
    -----
    Any Tk application must run in the (or at least *a*) main thread.
    Therefore, the real game needs to run in some background thread, or
    the Tk application needs to have its own process. (Note that using
    Python’s subprocess library might have it’s very own issues with Tk.)

    This means that we’ll need to exchange all information about current
    universe states in a thread-safe and location independent way. A good way
    to accomplish this is using a zmq socket.

    There is however a problem with a simple message passing approach: The
    producer (ie. the GameMaster) may produce new states much faster than the
    consumer is able to process them. (ie. the Viewer might show some
    animations which just take their time.)
    A message queue which is just naïvely filled might therefore be a
    suboptimal solution when the game is finished long before the animations.

    This synchronisation could be accomplished using a separate messaging
    scheme which tells the main game that it should move on.

    Parameters
    ----------
    address : zmq uri
        The address of the zmq socket to connect to
    geometry: tuple, default = None
        The size (in pixel) of the game root window. None means
        using a bit less than the screen size.

    Attributes
    ----------
    root : The Tk root instance
    app : The TkApplication class

    """
    def __init__(self, address, controller_address=None, geometry=None, delay=1):
        self.address = address
        self.controller_address = controller_address
        self.delay = delay
        self.geometry = geometry

    def run(self):
        self.root = tkinter.Tk()
        if self.geometry is None:
            root_geometry = '900x510'
        else:
            root_geometry = str(self.geometry[0])+'x'+str(self.geometry[1])
        # put the root window in some sensible position
        self.root.geometry(root_geometry+'+40+40')

        self.app = TkApplication(master=self.root,
                                 address=self.address,
                                 controller_address=self.controller_address,
                                 geometry=self.geometry,
                                 delay=self.delay)
        # schedule next read
        self.root.after_idle(self.app.read_queue)
        try:
            # Try our best to get the application to the front.
            self.root.lift()
            force_frontmost()

            self.root.mainloop()
        except KeyboardInterrupt:
            pass
