# -*- coding: utf-8 -*-

from Tkinter import *

import cmath

from pelita.datamodel import create_CTFUniverse
from pelita import datamodel
from pelita.layout import Layout

def col(*rgb):
    return "#%02x%02x%02x" % rgb

def rotate(arc, rotation):
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

        self.mesh = mesh

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
        self.direction = 0
        self.score = 0

    def rotate(self, darc):
        self.direction += darc
        self.direction %= 360

    def rotate_to(self, arc):
        self.direction = arc % 360
        print self.direction

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
            n = cmath.rect(scale * 0.85, a * cmath.pi / 180.0)
            coords.append((n.real + self.x, n.imag + self.y))
            n = cmath.rect(scale * 0.3, i * cmath.pi / 180.0)
            coords.append((n.real + self.x, n.imag + self.y))

        canvas.create_polygon(width=0.05 * scale, fill="", outline=col(94, 158, 217), *coords)

class Wall(TkSprite):
    def draw(self, canvas):
        canvas.create_oval(self.box(0.3), fill=col(94, 158, 217), tag=self.tag)

class Food(TkSprite):
    def draw(self, canvas):
        canvas.create_oval(self.box(0.3), fill=col(217, 158, 158), tag=self.tag)

class UiCanvas(Canvas):
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
        item.move(self.canvas, x * self.scale, y * self.scale)

class TkApplication(Frame):
    def createWidgets(self, graph):
        self.canvas = UiCanvas(self, graph)

    def __init__(self, graph, master=None):
        Frame.__init__(self, master) # old style
        self.pack()
        self.createWidgets(graph)

import threading
import time

class Animation(threading.Thread):
    def __init__(self, delay, step_len=0.1):
        threading.Thread.__init__(self)
        # because we’re no more but a floating ghost, we become daemonic
        # so python does not wait for us when it wants to exit
        self.setDaemon(True)
        self.delay = delay
        self.step_len = 0.1

    @property
    def num_steps(self):
        return int(self.delay / self.step_len)

    def run(self):
        for step in range(self.num_steps):
            time.sleep(self.step_len)
            self.step()

    def step(self):
        raise NotImplementedError

    @classmethod
    def rotate(cls, canvas, item, arc, delay=0.5, step_len=0.1):
        anim = cls(delay, step_len)
        step_arc = float(arc) / anim.num_steps
        def rotation():
            item.rotate(step_arc)
            item.redraw(canvas.canvas)

        anim.step = rotation
        return anim

    @classmethod
    def rotate_to(cls, canvas, item, arc, delay=0.5, step_len=0.1):
        anim = cls(delay, step_len)
        s_arc = (item.direction - arc) % 360 - 180

        step_arc = float(s_arc) / anim.num_steps
        def rotation():
            item.rotate(step_arc)
            item.redraw(canvas.canvas)

        anim.step = rotation
        return anim

    @classmethod
    def move(cls, canvas, item, transpos, delay=0.5, step_len=0.1):
        anim = cls(delay, step_len)
        dx = float(transpos[0]) / anim.num_steps
        dy = float(transpos[1]) / anim.num_steps
        def translation():
            canvas.move(item, dx, dy)
            #item.redraw(canvas.canvas)

        anim.step = translation
        return anim

    @classmethod
    def sequence(cls, *anims):
        def seq():
            for anim in anims:
                anim.start()
                anim.join()
        anim = threading.Thread(target=seq)
        anim.setDaemon(True)
        return anim

from pelita.messaging import Notification
from pelita.messaging import DispatchingActor, expose, actor_of

class CanvasActor(DispatchingActor):
    @expose
    def go_to(self, message, direction):
        pos = complex(direction[0], - direction[1])
        arc = int(cmath.phase(pos) / cmath.pi * 180)

        anim_seq = Animation.sequence(
            Animation.rotate_to(canvas, canvas.registered_items[9], arc),
            Animation.move(canvas, canvas.registered_items[9], direction, step_len=0.1),
        )
        anim_seq.start()
        anim_seq.join()

        print direction

East = Notification("go_to", [(1, 0)])
West = Notification("go_to", [(-1, 0)])
South = Notification("go_to", [(0, 1)])
North = Notification("go_to", [(0, -1)])


if __name__ == "__main__":

    root = Tk()



    test_layout = (
            """ ########
                #0     #
                #  .   #
                #    1 #
                ######## """)

    mesh = create_CTFUniverse(Layout.strip_layout(test_layout), 2).maze

    scale = 60
    mesh_graph = MeshGraph(mesh.height, mesh.width, mesh.height * scale, mesh.width * scale)

    app = TkApplication(mesh_graph, master=root)

    mesh[3,3] = "."

    canvas = app.canvas

    canvas.draw_mesh(mesh)

    def move():
        time.sleep(3)
        canvas.move(canvas.registered_items[4], 2, 1)
        canvas.move(canvas.registered_items[9], 2, 1)
        canvas.registered_items[9].rotate(30)
        canvas.registered_items[9].redraw(canvas.canvas)

    thread = threading.Thread(target=move)
    thread.setDaemon(True)
    #thread.start()

    actor = actor_of(CanvasActor)
    actor.start()
    actor.put(South)
    actor.put(East)
    actor.put(North)
    actor.put(West)

    anim_seq = Animation.sequence(
        Animation.rotate(canvas, canvas.registered_items[9], 90),
        Animation.move(canvas, canvas.registered_items[9], (1, 2), delay=5, step_len=0.1),
        )
    #anim_seq.start()

    app.mainloop()
    root.destroy()