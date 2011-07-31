# -*- coding: utf-8 -*-

from Tkinter import *

import Queue
import math
import cmath

from pelita.datamodel import create_CTFUniverse
from pelita import datamodel
from pelita.layout import Layout

def col(*rgb):
    return "#%02x%02x%02x" % rgb

def rotate(arc, rotation):
    """Helper for rotation normalisation."""
    return (arc + rotation) % 360

class MeshGraph(object):
    """ A `MeshGraph` is a structure of `num_x` * `num_y` rectangles,
    covering an area of `height` * `width`.
    """
    def __init__(self, num_x, num_y, height, width):
        self.num_x = num_x
        self.num_y = num_y
        self.height = height
        self.width = width

        self.rect_height = float(height) / num_x
        self.rect_width = float(width) / num_y

        self.half_scale_x = self.rect_height / 2.0
        self.half_scale_y = self.rect_width / 2.0

    def mesh_to_real(self, mesh, coords):
        mesh_x, mesh_y = mesh
        coords_x, coords_y = coords

        real_x = self.mesh_to_real_x(mesh_x, coords_x)
        real_y = self.mesh_to_real_y(mesh_y, coords_y)
        return (real_x, real_y)

    def mesh_to_real_x(self, mesh_x, coords_x):
        # coords are between -1 and +1: shift on [0, 1]
        trafo_x = (coords_x + 1.0) / 2.0

        real_x = self.rect_height * (mesh_x + trafo_x)
        return real_x

    def mesh_to_real_y(self, mesh_y, coords_y):
        # coords are between -1 and +1: shift on [0, 1]
        trafo_y = (coords_y + 1.0) / 2.0

        real_y = self.rect_width * (mesh_y + trafo_y)
        return real_y

class TkSprite(object):
    def __init__(self, mesh):
        self.x = 0
        self.y = 0
        self.height = 1
        self.width = 1
        self.is_hidden = True

        self.direction = 0

        self.mesh = mesh

    def rotate(self, darc):
        pass

    def rotate_to(self, arc):
        pass

    @property
    def position(self):
        if self.is_hidden:
            return (0, 0)
        return (self.x, self.y)

    @position.setter
    def position(self, position):
        self.x = position[0]
        self.y = position[1]

    def hide(self):
        self.is_hidden = True

    def show(self):
        self.is_hidden = False

    def draw(self, canvas):
        raise NotImplementedError

    def box(self, factor=1.0):
        return ((self.x) - self.width * factor * self.mesh.half_scale_x, (self.y) - self.height * factor * self.mesh.half_scale_y,
                (self.x) + self.width * factor * self.mesh.half_scale_x, (self.y) + self.height * factor * self.mesh.half_scale_y)

    @property
    def tag(self):
        return "tag" + str(id(self))

    def move(self, canvas, dx, dy):
        self.x += dx
        self.y += dy
        canvas.move(self.tag, dx, dy)

    def redraw(self, canvas):
        canvas.delete(self.tag)
        self.draw(canvas)

class BotSprite(TkSprite):
    def __init__(self, scale):
        super(BotSprite, self).__init__(scale)
        self.score = 0

    def rotate(self, darc):
        self.direction += darc
        self.direction %= 360

    def rotate_to(self, arc):
        self.direction = arc % 360

    def draw_bot(self, canvas, outer_col, eye_col, central_col=col(235, 235, 50)):
        bounding_box = self.box()
        scale = (self.mesh.half_scale_x + self.mesh.half_scale_y) * 0.5 # TODO: what, if x >> y?

        direction = self.direction
        rot = lambda x: rotate(x, direction)

        #canvas.create_oval(self.box(1.1), width=0.25 * scale, outline="black", tag=self.tag)

        canvas.create_arc(bounding_box, start=rot(30), extent=300, style="arc", width=0.2 * scale, outline=outer_col, tag=self.tag)
        canvas.create_arc(bounding_box, start=rot(-20), extent=15, style="arc", width=0.2 * scale, outline=outer_col, tag=self.tag)
        canvas.create_arc(bounding_box, start=rot(5), extent=15, style="arc", width=0.2 * scale, outline=outer_col, tag=self.tag)

        canvas.create_arc(bounding_box, start=rot(-30), extent=10, style="arc", width=0.2 * scale, outline=eye_col, tag=self.tag)
        canvas.create_arc(bounding_box, start=rot(20), extent=10, style="arc", width=0.2 * scale, outline=eye_col, tag=self.tag)

        canvas.create_arc(bounding_box, start=rot(-5), extent=10, style="arc", width=0.2 * scale, outline=central_col, tag=self.tag)

        score = self.score
        canvas.create_text(self.x, self.y, text=score, font=(None, int(0.5 * scale)), tag=self.tag)


class Harvester(BotSprite):
    def draw(self, canvas):
        self.draw_bot(canvas, outer_col=col(94, 158, 217), eye_col=col(235, 60, 60))

class Destroyer(BotSprite):
    def draw(self, canvas):
        self.draw_bot(canvas, outer_col=col(235, 90, 90), eye_col=col(94, 158, 217))
        self.draw_polygon(canvas)

    def draw_polygon(self, canvas):
        scale = (self.mesh.half_scale_x + self.mesh.half_scale_y) * 0.5 # TODO: what, if x >> y?

        direction = 110

        penta_arcs = range(0 - direction, 360 - direction, 360 / 5)
        penta_arcs_inner = [arc + 360 / 5 / 2.0 for arc in penta_arcs]

        coords = []
        for a, i in zip(penta_arcs, penta_arcs_inner):
            # we rotate with the help of complex numbers
            n = cmath.rect(scale * 0.85, math.radians(a))
            coords.append((n.real + self.x, n.imag + self.y))
            n = cmath.rect(scale * 0.3, math.radians(i))
            coords.append((n.real + self.x, n.imag + self.y))

        canvas.create_polygon(width=0.05 * scale, fill="", outline=col(94, 158, 217), *coords)

class Wall(TkSprite):
    def draw(self, canvas):
        canvas.create_oval(self.box(0.3), fill=col(94, 158, 217), tag=self.tag)

class Food(TkSprite):
    def draw(self, canvas):
        canvas.create_oval(self.box(0.3), fill=col(217, 158, 158), tag=self.tag)

class UiCanvas(object):
    def __init__(self, master, mesh_graph):
        self.mesh_graph = mesh_graph

        self.master = master
        self.canvas = Canvas(self.master, width=self.mesh_graph.width, height=self.mesh_graph.height)
        self.canvas.pack()

        self.registered_items = []
        self.mapping = {
            datamodel.Wall: Wall,
            datamodel.Food: Food
        }

    def draw_mesh(self, mesh):
        for position, items in mesh.iteritems():
            x, y = position
            self.draw_items(items, x, y)

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

        item.position = self.mesh_graph.mesh_to_real((x, y), (0, 0))

        item.show()
        item.draw(self.canvas)

    def move(self, item, x, y):
        item.move(self.canvas, x * self.mesh_graph.rect_width, y * self.mesh_graph.rect_height)

class TkApplication(Frame):
    def __init__(self, graph, queue, master=None):
        Frame.__init__(self, master) # old style
        self.pack()
        self.create_widgets(graph)
        self.queue = queue

        self.animations = []

    def start_drawing(self):
        self.redraw()
        self.update_application()

    def create_widgets(self, graph):
        self.canvas = UiCanvas(self, graph)

    def update_application(self):
        try:
            event = self.queue.get(False)
            print "got", event
            self.react(event)
            self.after(3000, self.update_application)
        except Queue.Empty:
            self.quit()

    def redraw(self):
        for anim in self.animations:
            anim.step()

        self.after(100, self.redraw)

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

import threading
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
            pos_x = anim.old_pos_x + dx * rate
            pos_y = anim.old_pos_y + dy * rate

            item.position = pos_x, pos_y
            item.redraw(canvas.canvas)
            #item.redraw(canvas.canvas)

        anim._step = translate
        return anim



from pelita.messaging import Notification
from pelita.messaging import DispatchingActor, expose, actor_of

East = Notification("go_to", [(1, 0)]).dict
West = Notification("go_to", [(-1, 0)]).dict
South = Notification("go_to", [(0, 1)]).dict
North = Notification("go_to", [(0, -1)]).dict


if __name__ == "__main__":
    import logging
    logging.basicConfig()

    test_layout = (
            """ ########
                #0     #
                #  .   #
                #    1 #
                ######## """)

    mesh = create_CTFUniverse(Layout.strip_layout(test_layout), 2).maze

    scale = 60
    mesh_graph = MeshGraph(mesh.height, mesh.width, mesh.height * scale, mesh.width * scale)

    event_queue = Queue.Queue()
    app = TkApplication(mesh_graph, event_queue)

    class CanvasActor(DispatchingActor):
        @expose
        def go_to(self, message, direction):
            event_queue.put(direction)


    mesh[3,3] = "."

    canvas = app.canvas
    canvas.draw_mesh(mesh)

    actor = actor_of(CanvasActor)
    actor.start()

    app.on_quit = actor.stop

    actor.put(South)
    actor.put(East)
    actor.put(North)
    actor.put(West)

    #anim_seq = Animation.sequence(
    #    Animation.rotate(canvas, canvas.registered_items[9], 90),
    #    Animation.move(canvas, canvas.registered_items[9], (1, 2), delay=5, step_len=0.1),
    #    )
    #anim_seq.start()

    app.after_idle(app.start_drawing)
    app.mainloop()
