# -*- coding: utf-8 -*-

import cmath
import math

def col(red, green, blue):
    """Convert the given colours [0, 255] to HTML hex colours."""
    return "#%02x%02x%02x" % (red, green, blue)

def rotate(arc, rotation):
    """Helper for rotation normalisation."""
    return (arc + rotation) % 360

class TkSprite(object):
    def __init__(self, mesh, x=0, y=0, direction=0):
        self.mesh = mesh

        self.x = x
        self.y = y

        self.direction = direction

    @property
    def position(self):
        return (self.x, self.y)

    @position.setter
    def position(self, position):
        old = self.x - self.y * 1j

        self.x = position[0]
        self.y = position[1]

        new = self.x - self.y * 1j
        # automatic rotation
#        if new != old:
#            self.direction = math.degrees(cmath.phase(new - old))

    @property
    def real_position(self):
        return self.mesh.mesh_to_real((self.x, self.y), (0, 0))

    def real(self, shift=(0, 0)):
        return self.mesh.mesh_to_real((self.x, self.y), shift)

    def draw(self, canvas):
        raise NotImplementedError

    def box(self, factor=1.0):
        return (self.real((-factor, -factor)),
                self.real((+factor, +factor)))

    @property
    def tag(self):
        return "tag" + str(id(self))

    def move(self, canvas, dx, dy):
        self.x += dx
        self.y += dy
        canvas.move(self.tag, dx, dy)

    def moveto(self, canvas, x, y):
        self.x = x
        self.y = y
        self.redraw(canvas)

    def rotate(self, darc):
        self.direction += darc
        self.direction %= 360

    def rotate_to(self, arc):
        self.direction = arc % 360

    def redraw(self, canvas):
        canvas.delete(self.tag)
        self.draw(canvas)

class BotSprite(TkSprite):
    def __init__(self, mesh, score=0, bot_type=None, **kwargs):
        self.score = score

        self.bot_type = bot_type

        super(BotSprite, self).__init__(mesh, **kwargs)

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
        canvas.create_text(self.real_position[0], self.real_position[1], text=score, font=(None, int(0.5 * scale)), tag=self.tag)

    def draw(self, canvas):
        # A curious case of delegation
        args = dict(self.__dict__)
        self.bot_type(**args).draw(canvas)

class Harvester(BotSprite):
    def draw(self, canvas):
        self.draw_bot(canvas, outer_col=col(94, 158, 217), eye_col=col(235, 60, 60))

class Destroyer(BotSprite):
    def draw(self, canvas):
        self.draw_bot(canvas, outer_col=col(235, 90, 90), eye_col=col(94, 158, 217))
        self.draw_polygon(canvas)

    def draw_polygon(self, canvas):
        scale = (self.mesh.half_scale_x + self.mesh.half_scale_y) * 0.5 # TODO: what, if x >> y?

        direction = self.direction

        penta_arcs = [arc - direction for arc in range(0, 360, 360 / 5)]
        penta_arcs_inner = [arc + 360 / 5 / 2.0 for arc in penta_arcs]

        coords = []
        for a, i in zip(penta_arcs, penta_arcs_inner):
            # we rotate with the help of complex numbers
            n = cmath.rect(0.85, math.radians(a))
            coords.append((n.real, n.imag))
            n = cmath.rect(0.3, math.radians(i))
            coords.append((n.real, n.imag))

        coords = [self.real(coord) for coord in coords]
        canvas.create_polygon(width=0.05 * scale, fill="", outline=col(94, 158, 217), *coords)

class Wall(TkSprite):
    def draw(self, canvas):
        canvas.create_oval(self.box(0.3), fill=col(94, 158, 217), tag=self.tag)

class Food(TkSprite):
    def draw(self, canvas):
        canvas.create_oval(self.box(0.3), fill=col(217, 158, 158), tag=self.tag)
