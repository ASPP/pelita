# -*- coding: utf-8 -*-

import Queue

from pelita.viewer import AbstractViewer
from pelita.ui.tk_canvas import TkApplication

class TkViewer(AbstractViewer):
    def __init__(self):
        self.observe_queue = Queue.Queue()
        self.viewer = TkApplication(queue=self.observe_queue)
        self.viewer.after_idle(self.viewer.read_queue)

    def observe(self, round_, turn, universe, events):
        print "observed", events
        import time
        time.sleep(0.5)
        import copy
        self.observe_queue.put(copy.deepcopy({
            "round": round_,
            "turn": turn,
            "universe": universe,
            "events": events}))
