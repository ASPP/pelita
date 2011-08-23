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
    def __init__(self, mesh, x=0, y=0, direction=0, _tag=None):
        self.mesh = mesh

        self.x = x
        self.y = y

        self._tag = _tag

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

    def screen(self, shift=(0, 0)):
        return self.mesh.mesh_trafo(self.x, self.y).screen(*shift)

    def draw(self, canvas, universe=None):
        raise NotImplementedError

    def bounding_box(self, scale_factor=1.0):
        return (self.screen((- scale_factor, - scale_factor)),
                self.screen((+ scale_factor, + scale_factor)))

    @property
    def tag(self):
        _tag = self._tag or "tag" + str(id(self))
        return _tag

    def redraw(self, canvas, universe=None):
        self.delete(canvas)
        self.draw(canvas, universe)

    def delete(self, canvas):
        canvas.delete(self.tag)

class BotSprite(TkSprite):
    def __init__(self, mesh, team=0, bot_idx=0, **kwargs):
        self.bot_idx = bot_idx
        self.team = team

        super(BotSprite, self).__init__(mesh, **kwargs)

    def draw_bot(self, canvas, outer_col, eye_col, mirror=False):
        direction = self.direction

        # bot body
        canvas.create_arc(self.bounding_box(), start=rotate(20, direction), extent=320, style="pieslice",
                          width=0, outline=outer_col, fill=outer_col, tag = self.tag)

        # bot eye
        # first locate eye in the center
        eye_size = 0.15
        eye_box = (-eye_size -eye_size*1j, eye_size + eye_size*1j)
        # shift it to the middle of the bot just over the mouth
        # take also care of mirroring
        mirror = -1 if mirror else 1
        eye_box = [item+ 0.4 + mirror*0.6j for item in eye_box]
        # rotate based on direction
        eye_box = [cmath.exp(1j*math.radians(-direction)) * item for item in eye_box]
        eye_box = [self.screen((item.real, item.imag)) for item in eye_box]
        canvas.create_oval(eye_box, fill=eye_col, width=0, tag=self.tag)

    def draw(self, canvas, universe):
        is_harvester = universe.bots[self.bot_idx].is_harvester
        if is_harvester:
            if self.team == 0:
                self.draw_bot(canvas, outer_col=col(94, 158, 217), eye_col="yellow", mirror=True)
            else:
                self.draw_bot(canvas, outer_col=col(235, 90, 90), eye_col="yellow")
        else:
            if self.team == 0:
                self.draw_destroyer(canvas, outer_col=col(94, 158, 217), eye_col="yellow", mirror=True)
            else:
                self.draw_destroyer(canvas, outer_col=col(235, 90, 90), eye_col="yellow")

    def draw_destroyer(self, canvas, outer_col, eye_col, mirror=False):
        direction = self.direction
        box_ll, box_tr = self.bounding_box()

        # ghost head
        canvas.create_arc((box_ll, box_tr), start=0, extent=180, style="pieslice",
                          width=0, outline=outer_col, fill=outer_col, tag = self.tag)
        # ghost body
        box_ll = box_ll[0], box_ll[1] + (box_tr[1]-box_ll[1])/2.
        amplitude = (box_tr[1]-box_ll[1])/4.
        start = box_ll[0], box_tr[1]-amplitude/2.
        end = box_tr[0], start[1]
        periods = 3
        period = (end[0]-start[0])/periods
        points_per_period = 10
        x_spacing = period/points_per_period
        x = [start[0]+i*x_spacing for i in range(periods*points_per_period)]
        x.append(end[0])
        y = [amplitude*math.cos(2*math.pi*(x_i-start[0])/period) + start[1] for x_i in x]
        # add container edges for the polygon
        x.insert(0, box_ll[0]); y.insert(0, box_ll[1] - 1)
        x.append(box_tr[0]); y.append(box_ll[1] - 1)
        canvas.create_polygon(zip(x,y), width=1, outline=outer_col, fill=outer_col, tag=self.tag)

        # ghost eyes
        eye_size = 0.15
        eye_box = (-eye_size -eye_size*1j, eye_size + eye_size*1j)
        # right eye
        eye_box_r = [item+ 0.4 - 0.5j for item in eye_box]
        eye_box_r = [self.screen((item.real, item.imag)) for item in eye_box_r]
        canvas.create_oval(eye_box_r, fill=eye_col, width=0, tag=self.tag)
        # left eye
        eye_box_l = [item- 0.4 - 0.5j for item in eye_box]
        eye_box_l = [self.screen((item.real, item.imag)) for item in eye_box_l]
        canvas.create_oval(eye_box_l, fill=eye_col, width=0, tag=self.tag)

class Wall(TkSprite):
    def draw(self, canvas, universe=None):
        scale = (self.mesh.half_scale_x + self.mesh.half_scale_y) * 0.5
        if not ((0, 1) in self.wall_neighbours or
                (1, 0) in self.wall_neighbours or
                (0, -1) in self.wall_neighbours or
                (-1, 0) in self.wall_neighbours):
            # if there is no direct neighbour, we can’t connect.
            # draw only a small dot.
            # TODO add diagonal lines
            canvas.create_line(self.screen((-0.3, 0)), self.screen((+0.3, 0)), fill=col(48, 26, 22),
                               width=0.8 * scale, tag=(self.tag, "wall"), capstyle="round")
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
                            canvas.create_line(self.screen((0, 0)), self.screen((2*dx, 2*dy)), fill=col(48, 26, 22),
                                               width=0.8 * scale, tag=(self.tag, "wall"), capstyle="round")

class Food(TkSprite):
    @classmethod
    def food_pos_tag(cls, position):
        return "Food" + str(position)

    def draw(self, canvas, universe=None):
        if self.position[0] < self.mesh.num_x/2:
            fill = col(94, 158, 217)
        else:
            fill = col(235, 90, 90)
        canvas.create_oval(self.bounding_box(0.4), fill=fill, width=0, tag=(self.tag, self.food_pos_tag(self.position), "food"))
