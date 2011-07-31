# -*- coding: utf-8 -*-

from Tkinter import *

import Queue

from pelita.datamodel import create_CTFUniverse
from pelita import datamodel
from pelita.layout import Layout

from pelita.ui.tk_sprites import *

class MeshGraph(object):
    """ A `MeshGraph` is a structure of `num_x` * `num_y` rectangles,
    covering an area of `width`, `height`.
    """
    def __init__(self, num_x, num_y, width, height):
        self.num_x = num_x
        self.num_y = num_y
        self.height = height
        self.width = width

    @property
    def rect_width(self):
        return float(self.width) / self.num_x

    @property
    def rect_height(self):
        return float(self.height) / self.num_y

    @property
    def half_scale_x(self):
        return self.rect_width / 2.0

    @property
    def half_scale_y(self):
        return self.rect_height / 2.0

    def mesh_to_real(self, mesh, coords):
        mesh_x, mesh_y = mesh
        coords_x, coords_y = coords

        real_x = self.mesh_to_real_x(mesh_x, coords_x)
        real_y = self.mesh_to_real_y(mesh_y, coords_y)
        return (real_x, real_y)

    def mesh_to_real_x(self, mesh_x, coords_x):
        # coords are between -1 and +1: shift on [0, 1]
        trafo_x = (coords_x + 1.0) / 2.0

        real_x = self.rect_width * (mesh_x + trafo_x)
        return real_x

    def mesh_to_real_y(self, mesh_y, coords_y):
        # coords are between -1 and +1: shift on [0, 1]
        trafo_y = (coords_y + 1.0) / 2.0

        real_y = self.rect_height * (mesh_y + trafo_y)
        return real_y

class UiCanvas(object):
    def __init__(self, master):
        self.mesh_graph = None

        self.master = master
        self.canvas = None

        self.registered_items = []
        self.mapping = {
            datamodel.Wall: Wall,
            datamodel.Food: Food
        }

    def init_canvas(self):
        self.canvas = Canvas(self.master, width=self.mesh_graph.width, height=self.mesh_graph.height)
        self.canvas.pack(fill=BOTH, expand=YES)
        self.canvas.bind('<Configure>', self.resize)

    def update(self, universe):
        print "update"
        if not self.canvas:
            if not self.mesh_graph:
                width = universe.maze.width
                height = universe.maze.height
                scale = 60
                self.mesh_graph = MeshGraph(width, height, scale * width, scale * height)
            self.init_canvas()

        self.mesh_graph.num_x = universe.maze.width
        self.mesh_graph.num_y = universe.maze.height
        self.clear()
        self.draw_mesh(universe.maze)
        self.draw_bots(universe)

    def clear(self):
        self.canvas.delete(ALL)

    def resize(self, event):
        print '(%d, %d)' % (event.width, event.height)
        self.mesh_graph.width = event.width
        self.mesh_graph.height = event.height

    def draw_mesh(self, mesh):
        for position, items in mesh.iteritems():
            x, y = position
            self.draw_items(items, x, y)

    def draw_bots(self, universe):
        for bot in universe.bots:
            pos = bot.current_pos
            if bot.is_harvester:
                tk_bot = Harvester(self.mesh_graph)
            else:
                tk_bot = Destroyer(self.mesh_graph)
            tk_bot.position = pos
            tk_bot.score = universe.teams[bot.team_index].score
            tk_bot.show()
            tk_bot.draw(self.canvas)

    def draw_items(self, items, x, y):
        item_class = None
        for item in items:
            for key in self.mapping:
                if isinstance(item, key):
                    item_class = self.mapping[key]

        if not item_class:
            return

        item = item_class(self.mesh_graph)
        self.registered_items.append(item)

        item.position = x, y

        item.show()
        item.draw(self.canvas)

    def move(self, item, x, y):
        item.move(self.canvas, x * self.mesh_graph.rect_width, y * self.mesh_graph.rect_height)

class TkApplication(Frame):
    def __init__(self, queue, master=None):
        Frame.__init__(self, master) # old style

        self.queue = queue

        self.pack(fill=BOTH, expand=YES)
        self.ui_canvas = UiCanvas(self)

        self.animations = []

    def read_queue(self):
        try:
            # read all events.
            # if queue is empty, try again in 500 ms
            while True:
                observed = self.queue.get(False)
                self.observe(observed)
        except Queue.Empty:
            self.after(500, self.read_queue)

    def observe(self, observed):
        round = observed["round"]
        turn = observed["turn"]
        universe = observed["universe"]
        events = observed["events"]

        self.ui_canvas.update(universe)

    def redraw(self):
        for anim in self.animations:
            anim.step()

        self.canvas.canvas.update_idletasks()
        self.after(10, self.redraw)

    def react(self, event):
        direction = event
        pos = complex(direction[0], - direction[1])
        arc = math.degrees(cmath.phase(pos))

        anim_seq = [
            Animation.rotate_to(canvas, canvas.registered_items[8], arc),
            Animation.move(canvas, canvas.registered_items[8], direction),
        ]
        [anim.start() for anim in anim_seq]
        self.animations += anim_seq

        print direction

    def on_quit(self):
        """ override for things which must be done when we exit.
        """
        pass

    def quit(self):
        self.on_quit()
        Frame.quit(self)

import time

class Animation(object):
    def __init__(self, duration):
        self.duration = duration
        self.start_time = None
        self.is_finished = False

    def elapsed(self):
        if self.start_time is None:
            raise AttributeError("Animation is not running.")
        return time.time() - self.start_time

    def start(self):
        self.start_time = time.time()

    def rate(self):
        rate = self.elapsed() / self.duration
        if rate > 1:
            self.is_finished = True
            return 1
        return rate

    def step(self):
        if not self.is_finished:
            self._step()

    def _step(self):
        raise NotImplementedError

    def finish(self):
        raise NotImplementedError

    @classmethod
    def rotate(cls, canvas, item, arc, duration=0.5):
        anim = cls(duration)
        step_arc = float(arc)
        def rotate():
            item.rotate(step_arc * anim.rate())
            item.redraw(canvas.canvas)

        anim._step = rotate
        return anim

    @classmethod
    def rotate_to(cls, canvas, item, arc, duration=0.5):
        anim = cls(duration)
        s_arc = (item.direction - arc) % 360 - 180

        step_arc = float(s_arc)
        def rotate():
            item.rotate(step_arc * anim.rate())
            item.redraw(canvas.canvas)

        anim._step = rotate
        return anim

    @classmethod
    def move(cls, canvas, item, transpos, duration=0.5):
        anim = cls(duration)
        dx = float(transpos[0]) * canvas.mesh_graph.rect_height
        dy = float(transpos[1]) * canvas.mesh_graph.rect_width
        anim.old_pos_x = item.position[0]
        anim.old_pos_y = item.position[1]

        anim.last_rate = 0
        def translate():
            rate = anim.rate()
            rate = math.sin(rate * math.pi * 0.5)
            pos_x = anim.old_pos_x + dx * rate
            pos_y = anim.old_pos_y + dy * rate

            item.moveto(canvas.canvas, pos_x, pos_y)

        anim._step = translate
        return anim
