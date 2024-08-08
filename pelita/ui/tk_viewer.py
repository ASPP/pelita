import json
import logging
import os
import shutil
import sys

import tkinter
import zmq

from .tk_canvas import TkApplication

_logger = logging.getLogger(__name__)

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
    def __init__(self, address, controller_address=None, geometry=None, delay=1, stop_after=None, fullscreen=False):
        self.address = address
        self.controller_address = controller_address
        self.delay = delay
        self.geometry = geometry if geometry else (900, 580)
        self.fullscreen = fullscreen
        self.stop_after = stop_after

        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.setsockopt_unicode(zmq.SUBSCRIBE, "")
        self.socket.connect(self.address)
        self.poll = zmq.Poller()
        self.poll.register(self.socket, zmq.POLLIN)

        self._delay = 2

    def run(self):
        try:
            self.root = tkinter.Tk()
        except tkinter.TclError as e:
            _logger.error('TclError: %s. Exiting.', e)
            if self.controller_address:
                # We should be controlling the server. But we can’t.
                # Send exit.
                # TODO: This should flag an error code back to the server.
                context = zmq.Context()
                controller_socket = context.socket(zmq.DEALER)
                controller_socket.connect(self.controller_address)
                controller_socket.send_json({"__action__": "exit"})
            sys.exit(-1)
        if self.fullscreen:
            self.root.attributes('-fullscreen',True)
        else:
            root_geometry = str(self.geometry[0])+'x'+str(self.geometry[1])
            # put the root window in some sensible position
            self.root.geometry(root_geometry+'+40+40')

        self.app = TkApplication(window=self.root,
                                 controller_address=self.controller_address,
                                 geometry=self.geometry,
                                 delay=self.delay,
                                 stop_after=self.stop_after, fullscreen=self.fullscreen)
        # schedule next read
        self.root.after_idle(self.read_queue)
        try:
            # Try our best to get the application to the front.
            self.root.lift()
            force_frontmost()

            self.root.mainloop()
        except KeyboardInterrupt:
            pass

    def read_queue(self):
        # We increase the polling delay up to 100ms each try to avoid
        # using too much cpu when there are no messages anyway.
        if self._delay > 100:
            self._delay = 100
        try:
            # read all events.
            # if queue is empty, try again in a few ms
            # we don’t want to block here and lock
            # Tk animations
            message = self.socket.recv_unicode(flags=zmq.NOBLOCK)
            message = json.loads(message)

            _logger.debug(message["__action__"])
            # we currently don’t care about the action
            game_state = message["__data__"]
            if game_state:
                self.app.observe(game_state)

            self._delay = 2
            self._after(2, self.read_queue)
        except zmq.Again as e:
            _logger.debug('Nothing received. Waiting %.3d seconds.', self._delay)
            self._after(self._delay, self.read_queue)
            self._delay = self._delay * 2
        except zmq.ZMQError as e:
            _logger.info('ZMQ Error: %r. Ignoring.', e)
            self._after(self._delay, self.read_queue)
            self._delay = self._delay * 2

    def _after(self, delay, fun, *args):
        """ Execute fun(*args) after delay milliseconds.

        # Patched to quit after `KeyboardInterrupt`s.
        """
        def wrapped_fun():
            try:
                fun(*args)
            except KeyboardInterrupt:
                print("KBI")
                _logger.info("Detected KeyboardInterrupt. Exiting.")
                self.quit()
        self.root.after(delay, wrapped_fun)
