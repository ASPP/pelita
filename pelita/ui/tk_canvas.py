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

        self.waiting_animations = []

    def init_canvas(self):
        self.canvas = Canvas(self.master, width=self.mesh_graph.width, height=self.mesh_graph.height)
        self.canvas.pack(fill=BOTH, expand=YES)
        self.canvas.bind('<Configure>', self.resize)

    def update(self, events=None, universe=None):
        if not self.canvas:
            if not self.mesh_graph:
                width = universe.maze.width
                height = universe.maze.height
                scale = 60
                self.mesh_graph = MeshGraph(width, height, scale * width, scale * height)

                self.bot_sprites = {}

            self.init_canvas()
            self.init_bots(universe)

        if universe:
            self.mesh_graph.num_x = universe.maze.width
            self.mesh_graph.num_y = universe.maze.height

        if events:
            move_events = events.filter_type(datamodel.BotMoves)
            for move_event in move_events:
                bot_idx = move_event.bot_index
                bot_sprite = self.bot_sprites[bot_idx]

                old_pos = complex(*bot_sprite.position).conjugate()
                new_pos = complex(*universe.bots[bot_idx].current_pos).conjugate()

                direction = new_pos - old_pos

                arc = math.degrees(cmath.phase(direction))

                self.waiting_animations.append(Animation.sequence([
                    Animation.rotate_to(self, bot_sprite, arc, duration=0.2),
                    Animation.move_to(self, bot_sprite, (new_pos.real, - new_pos.imag), duration=0.2)
                ]))

        if self.waiting_animations:
            for animation in self.waiting_animations:

                if not animation.start_time:
                    animation.start()

                animation.step()
                self.canvas.update_idletasks()

            # delete finished
            self.waiting_animations = [anim for anim in self.waiting_animations if not anim.is_finished]

            # come back again
            self.canvas.after(10, self.update, None, universe)
            return

        if universe:
            #self.waiting_animations = []
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

    def init_bots(self, universe):
        for bot in universe.bots:
            bot_sprite = BotSprite(self.mesh_graph)

            self.bot_sprites[bot.index] = bot_sprite
            bot_sprite.position = bot.current_pos

            if bot.is_harvester:
                bot_sprite.bot_type = Harvester # Harvester(self.mesh_graph)
            else:
                bot_sprite.bot_type = Destroyer # (self.mesh_graph)

            bot_sprite.score = universe.teams[bot.team_index].score

    def draw_bots(self, universe):
        for bot_idx, bot_sprite in self.bot_sprites.iteritems():
            bot = universe.bots[bot_idx]

            bot_sprite.position = bot.current_pos

            if bot.is_harvester:
                bot_sprite.bot_type = Harvester # Harvester(self.mesh_graph)
            else:
                bot_sprite.bot_type = Destroyer # (self.mesh_graph)

            bot_sprite.score = universe.teams[bot.team_index].score
            bot_sprite.redraw(self.canvas)

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

        item.redraw(self.canvas)

    def move(self, item, x, y):
        item.move(self.canvas, x * self.mesh_graph.rect_width, y * self.mesh_graph.rect_height)

class TkApplication(Frame):
    def __init__(self, queue, master=None):
        Frame.__init__(self, master) # old style

        self.queue = queue

        self.pack(fill=BOTH, expand=YES)
        self.ui_canvas = UiCanvas(self)

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

        self.ui_canvas.update(events, universe)

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

    @property
    def is_finished(self):
        if self.start_time:
            if self.elapsed() / self.duration >= 1:
                return True
        return False

    def elapsed(self):
        if self.start_time is None:
            raise AttributeError("Animation is not running.")
        return time.time() - self.start_time

    def start(self):
        self.start_time = time.time()
        self._start()

    def rate(self):
        rate = self.elapsed() / self.duration
        if rate >= 1:
            return 1
        return rate

    def step(self):
        if not self.is_finished:
            self._step()

    def _start(self):
        pass

    def _step(self):
        raise NotImplementedError

    def finish(self):
        raise NotImplementedError

    @classmethod
    def rotate_to(cls, canvas, item, arc, duration=0.5):
        anim = cls(duration)

        def start():
            anim.old_direction = item.direction
            anim.diff_direction = (arc - anim.old_direction)

            anim.diff_direction = (anim.diff_direction + 180) % 360 - 180

        def rotate():
            rate = anim.rate()
            rate = math.sin(rate * math.pi * 0.5)
            new_dir = anim.old_direction + anim.diff_direction * rate

            item.direction = new_dir % 360
            item.redraw(canvas.canvas)

        anim._start = start
        anim._step = rotate
        return anim

    @classmethod
    def move_to(cls, canvas, item, new_pos, duration=0.5):
        anim = cls(duration)

        def start():
            anim.old_position = item.position
            anim.diff_position = (new_pos[0] - anim.old_position[0],
                                  new_pos[1] - anim.old_position[1])

        def translate():
            rate = anim.rate()
            rate = math.sin(rate * math.pi * 0.5)
            pos_x = anim.old_position[0] + anim.diff_position[0] * rate
            pos_y = anim.old_position[1] + anim.diff_position[1] * rate

            item.moveto(canvas.canvas, pos_x, pos_y)

        anim._start = start
        anim._step = translate
        return anim

    @classmethod
    def sequence(cls, animations):
        duration = sum(anim.duration for anim in animations)

        seq = cls(duration)
        seq.animations = animations
        seq.current_animation = None

        def step():
            if not seq.current_animation or seq.current_animation.is_finished:
                try:
                    seq.current_animation = seq.animations.pop(0)
                    seq.current_animation.start()
                except IndexError:
                    return
            print seq.animations
            seq.current_animation.step()

        seq._step = step
        return seq
