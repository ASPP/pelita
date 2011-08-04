# -*- coding: utf-8 -*-

import Tkinter
import Queue

from pelita import datamodel
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

        self.current_universe = None
        self.previous_universe = None

    def init_canvas(self):
        self.canvas = Tkinter.Canvas(self.master, width=self.mesh_graph.width, height=self.mesh_graph.height)
        self.canvas.pack(fill=Tkinter.BOTH, expand=Tkinter.YES)
        self.canvas.bind('<Configure>', self.resize)

    def update(self, events, universe):
        if not self.canvas:
            if not self.mesh_graph:
                width = universe.maze.width
                height = universe.maze.height
                scale = 60
                self.mesh_graph = MeshGraph(width, height, scale * width, scale * height)

                self.bot_sprites = {}

            self.init_canvas()
            self.init_bots(universe)

        self.previous_universe = self.current_universe
        self.current_universe = universe

        if not self.previous_universe:
            self.draw_universe(self.current_universe)
        else:
            self.draw_universe(self.previous_universe)

        self.draw_events(events)

    def draw_universe(self, universe):
        self.mesh_graph.num_x = universe.maze.width
        self.mesh_graph.num_y = universe.maze.height

        #self.waiting_animations = []
        self.clear()
        self.draw_mesh(universe.maze)
        self.draw_bots(universe)

    def draw_events(self, events=None):
        if events:
            destroy_events = events.filter_type(datamodel.BotDestroyed)
            destroy_animations = {}
            for destroy_event in destroy_events:
                destroyed_idx = destroy_event.harvester_index
                destroyed_sprite = self.bot_sprites[destroyed_idx]

                destroy_animations[destroyed_idx] = Animation.shrink(self, destroyed_sprite, duration=0.03)

            move_events = events.filter_type(datamodel.BotMoves)
            for move_event in move_events:
                bot_idx = move_event.bot_index
                bot_sprite = self.bot_sprites[bot_idx]

                old_pos = complex(*move_event.old_pos).conjugate()
                new_pos = complex(*move_event.new_pos).conjugate()

                direction = new_pos - old_pos

                arc = math.degrees(cmath.phase(direction))

                if direction != 0:
                    move_sequece = [
                        Animation.rotate_to(self, bot_sprite, arc, duration=0.02),
                        Animation.move_to(self, bot_sprite, (old_pos.real, -old_pos.imag), (new_pos.real, - new_pos.imag), duration=0.02)
                            ]
                else:
                    move_sequece = []

                if bot_idx in destroy_animations:
                    move_sequece.append(destroy_animations[bot_idx])
                    del destroy_animations[bot_idx]

                if move_sequece:
                    move_sequece.append(Animation.dummy(duration=0.02))
                    self.waiting_animations.append(Animation.sequence(move_sequece))

            for destroy_animation in destroy_animations.values():
                self.waiting_animations.append(destroy_animation)

            eat_events = events.filter_type(datamodel.BotEats)

        # disabling the animations for the moment
        self.waiting_animations = []
        if self.waiting_animations:
            for animation in self.waiting_animations:

                if not animation.start_time:
                    animation.start()

                # disabling the animations for the moment
                animation.step()

            # delete finished
            self.waiting_animations = [anim for anim in self.waiting_animations if not anim.is_finished]

            # come back again
            self.canvas.after(10, self.draw_events, None)

            tk_items = self.canvas.find_all()

            self.canvas.update_idletasks()
            return
        self.canvas.after(10, self.finish_events)

    def finish_events(self):
        self.draw_universe(self.current_universe)

    def clear(self):
        self.canvas.delete(Tkinter.ALL)

    def resize(self, event):
        self.mesh_graph.width = event.width
        self.mesh_graph.height = event.height

    def draw_mesh(self, mesh):
        for position, items in mesh.iteritems():
            x, y = position
            self.draw_items(items, x, y)

    def init_bots(self, universe):
        for bot in universe.bots:
            bot_sprite = BotSprite(self.mesh_graph, team=bot.team_index)

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

class TkApplication(Tkinter.Frame):
    def __init__(self, queue, master=None):
        Tkinter.Frame.__init__(self, master) # old style

        self.queue = queue

        self.pack(fill=Tkinter.BOTH, expand=Tkinter.YES)
        self.ui_canvas = UiCanvas(self)

    def read_queue(self):
        try:
            # read all events.
            # if queue is empty, try again in 500 ms
            while True:
                observed = self.queue.get(False)
                self.observe(observed)

                self.after(100, self.read_queue)
                return
        except Queue.Empty:
            self.after(100, self.read_queue)

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
        Tkinter.Frame.quit(self)

import time

class Animation(object):
    def __init__(self, duration):
        self.duration = duration
        self.start_time = None

    @property
    def is_finished(self):
        if self.start_time:
            if self.elapsed() / self.duration >= 1:
                self.finish()
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
            self.finish()
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
        self._finish()

    def _finish(self):
        pass

    @classmethod
    def shrink(cls, canvas, item, duration=0.5):
        anim = cls(duration)

        def start():
            anim.old_scale = item.additional_scale
            anim.diff_scale = (0 - anim.old_scale)

        def do_shrink():
            rate = anim.rate()
            new_scale = anim.old_scale + anim.diff_scale * rate

            item.additional_scale = new_scale
            item.redraw(canvas.canvas)

        def finish():
            item.additional_scale = anim.old_scale

        anim._start = start
        anim._step = do_shrink
        anim._finish = finish
        return anim

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
    def move_to(cls, canvas, item, from_pos, to_pos, duration=0.5):
        anim = cls(duration)

        def start():
            anim.old_position = from_pos
            anim.diff_position = (to_pos[0] - anim.old_position[0],
                                  to_pos[1] - anim.old_position[1])

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
    def dummy(cls, canvas=None, duration=0.1):
        anim = cls(duration)
        def do_nothing():
            pass
        anim._step = do_nothing
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
            seq.current_animation.step()

        def finish():
            for anim in seq.animations:
                anim.finish.is_finished

        seq._step = step
        seq._finish = finish
        return seq
