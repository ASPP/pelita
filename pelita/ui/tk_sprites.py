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
    def __init__(self, mesh, x=0, y=0, direction=0, _tag=None, additional_scale=1.0):
        self.mesh = mesh

        self.x = x
        self.y = y

        self._tag = _tag
        self.additional_scale = additional_scale

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
        if new != old:
            self.direction = math.degrees(cmath.phase(new - old))

    @property
    def real_position(self):
        return self.mesh.mesh_to_real((self.x, self.y), (0, 0))

    def real(self, shift=(0, 0)):
        return self.mesh.mesh_to_real((self.x, self.y), shift)

    def draw(self, canvas):
        raise NotImplementedError

    def box(self, factor=1.0):
        return (self.real((-factor * self.additional_scale, -factor * self.additional_scale)),
                self.real((+factor * self.additional_scale, +factor * self.additional_scale)))

    @property
    def tag(self):
        _tag = self._tag or "tag" + str(id(self))
        return _tag

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
    def __init__(self, mesh, score=0, bot_type=None, team=0, **kwargs):
        self.score = score
        self.team = team

        self.bot_type = bot_type

        super(BotSprite, self).__init__(mesh, **kwargs)

    def draw_bot(self, canvas, outer_col, eye_col):
        bounding_box = self.box()

        direction = self.direction
        # bot body
        canvas.create_oval(bounding_box, fill=outer_col, width=0, tag=self.tag)

        # bot mouth
        up = 1 + 0.3j
        down = 1 - 0.3j
        # rotate based on direction
        up = cmath.exp(1j*math.radians(-direction)) * up
        down = cmath.exp(1j*math.radians(-direction)) * down   
        coords = [self.real(coord) for coord in ((0,0), (up.real, up.imag), (down.real, down.imag))]
        canvas.create_polygon(fill="white", width=0, tag=self.tag, *coords)

        # bot eye
        # first locate eye in the center
        eye_size = 0.15
        eye_box = (-eye_size -eye_size*1j, eye_size + eye_size*1j)
        # shift it to the middle of the bot just over the mouth
        eye_box = [item+0.4+0.6j for item in eye_box]
        # rotate based on direction
        eye_box = [cmath.exp(1j*math.radians(-direction)) * item for item in eye_box]
        eye_box = [self.real((item.real, item.imag)) for item in eye_box] 
        canvas.create_oval(eye_box, fill=eye_col, width=0, tag=self.tag)

    def draw(self, canvas):
        # A curious case of delegation
        args = dict(self.__dict__)
        args["_tag"] = self.tag
        self.bot_type(**args).draw(canvas)

class Harvester(BotSprite):
    def draw(self, canvas):
        if self.team == 0:
            self.draw_bot(canvas, outer_col=col(94, 158, 217), eye_col="yellow")
        else:
            self.draw_bot(canvas, outer_col=col(235, 90, 90), eye_col="yellow")

class Destroyer(BotSprite):
    def draw(self, canvas):
        if self.team == 0:
            self.draw_bot(canvas, outer_col=col(94, 158, 217), eye_col="white")
        else:
            self.draw_bot(canvas, outer_col=col(235, 90, 90), eye_col="white")

class Wall(TkSprite):
    def draw(self, canvas):
        scale = (self.mesh.half_scale_x + self.mesh.half_scale_y) * 0.5
        if self.wall_neighbours == [(0,0)]:
            canvas.create_line(self.real((-0.3, 0)), self.real((+0.3, 0)), fill=col(48, 26, 22),
                               width=0.8 * scale, tag=self.tag, capstyle="round")
        else:            
            neighbours = [(-1, -1), (0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0)]
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if (dx, dy) in self.wall_neighbours:
                        if dx == dy == 0:
                            continue
                        if dx * dy != 0:
                            continue
                        index = neighbours.index((dx, dy))
                        if (neighbours[(index + 1) % len(neighbours)] in self.wall_neighbours and
                            neighbours[(index - 1) % len(neighbours)] in self.wall_neighbours):
                            pass
                        else:
                            canvas.create_line(self.real((0, 0)), self.real((2*dx, 2*dy)), fill=col(48, 26, 22),
                                               width=0.8 * scale, tag=self.tag, capstyle="round")

class Food(TkSprite):
    @classmethod
    def food_pos_tag(cls, position):
        return "Food" + str(position)

    def draw(self, canvas):
        canvas.create_oval(self.box(0.4), fill=col(96, 173, 57), width=0, tag=(self.tag, self.food_pos_tag(self.position)))
