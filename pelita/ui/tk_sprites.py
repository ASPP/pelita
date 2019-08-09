import cmath
import math


def col(red, green, blue):
    """Convert the given colours [0, 255] to HTML hex colours."""
    return "#%02x%02x%02x" % (red, green, blue)

RED = col(235, 90, 90)
BLUE = col(94, 158, 217)
YELLOW = col(242, 255, 83)
GREY = col(80, 80, 80)
BROWN = col(48, 26, 22)

def rotate(arc, rotation):
    """Helper for rotation normalisation."""
    return (arc + rotation) % 360

def pos_to_complex(pos):
    x, y = pos
    return x - y * 1j

class TkSprite:
    def __init__(self, mesh, *, position=None, _tag=None):
        self.mesh = mesh

        self._position = position
        self._direction = None
        self._tag = _tag

    @property
    def direction(self):
        return self._direction

    @property
    def position(self):
        return self._position

    @position.setter
    def position(self, position):
        if self.position is None or position is None:
            self._direction = None
            self._position = position
            return

        old_pos = self._position
        new_pos = position

        self._position = new_pos

        # automatic rotation
        if new_pos != old_pos:
            self._direction = math.degrees(cmath.phase(pos_to_complex(new_pos) - pos_to_complex(old_pos)))

    def screen(self, shift=(0, 0)):
        x, y = self.position
        return self.mesh.mesh_trafo(x, y).screen(*shift)

    def draw(self, canvas, game_state=None):
        raise NotImplementedError

    def bounding_box(self, scale_factor=1.0):
        return (self.screen((- scale_factor, - scale_factor)),
                self.screen((+ scale_factor, + scale_factor)))

    @property
    def tag(self):
        _tag = self._tag or "tag" + str(id(self))
        return _tag

    def redraw(self, canvas, game_state=None):
        self.delete(canvas)
        self.draw(canvas, game_state)

    def delete(self, canvas):
        canvas.delete(self.tag)

class BotSprite(TkSprite):
    def __init__(self, mesh, team=0, bot_id=0, **kwargs):
        self.bot_id = bot_id
        self.team = team
        self.width = mesh.mesh_width

        self.is_harvester = None

        super(BotSprite, self).__init__(mesh, **kwargs)

    def is_harvester_at(self, pos):
        if self.team == 0:
            return pos[0] >= self.width // 2
        elif self.team == 1:
            return pos[0] < self.width // 2

    def move_to(self, new_pos, canvas, game_state=None, force=None, say="", show_id=False):
        old_direction = self.direction
        old_position = self.position

        self.position = new_pos
        if (old_position is None
            or old_direction != self.direction
            or force
            or self.is_harvester != self.is_harvester_at(game_state['bots'][self.bot_id])):
            self.redraw(canvas, game_state)
        else:
            dx = self.position[0] - old_position[0]
            dy = self.position[1] - old_position[1]

            canvas.move(self.tag, self.mesh.rect_width * dx, self.mesh.rect_height * dy)

        canvas.delete("speak"+self.tag)
        # We increase readability with a white border around the text.
        canvas.create_text(self.bounding_box()[0][0]-1, self.bounding_box()[0][1], text=say, font=(None, 12), fill="white", tag="speak"+self.tag)
        canvas.create_text(self.bounding_box()[0][0]+1, self.bounding_box()[0][1], text=say, font=(None, 12), fill="white", tag="speak"+self.tag)
        canvas.create_text(self.bounding_box()[0][0], self.bounding_box()[0][1]-1, text=say, font=(None, 12), fill="white", tag="speak"+self.tag)
        canvas.create_text(self.bounding_box()[0][0], self.bounding_box()[0][1]+1, text=say, font=(None, 12), fill="white", tag="speak"+self.tag)
        canvas.create_text(self.bounding_box()[0][0], self.bounding_box()[0][1], text=say, font=(None, 12), fill="black", tag="speak"+self.tag)

        canvas.delete("show_id" + self.tag)
        # we print the bot_id in the lower left corner
        if show_id:
            local_idx = 0 if self.bot_id < 2 else 1
            shift = 4
            canvas.create_text(self.bounding_box()[0][0]-1 + shift, self.bounding_box()[1][1] - shift, text=local_idx, font=(None, 12), fill="white", tag="show_id"+self.tag)
            canvas.create_text(self.bounding_box()[0][0]+1 + shift, self.bounding_box()[1][1] - shift, text=local_idx, font=(None, 12), fill="white", tag="show_id"+self.tag)
            canvas.create_text(self.bounding_box()[0][0] + shift, self.bounding_box()[1][1]-1 - shift, text=local_idx, font=(None, 12), fill="white", tag="show_id"+self.tag)
            canvas.create_text(self.bounding_box()[0][0] + shift, self.bounding_box()[1][1]+1 - shift, text=local_idx, font=(None, 12), fill="white", tag="show_id"+self.tag)
            canvas.create_text(self.bounding_box()[0][0] + shift, self.bounding_box()[1][1] - shift, text=local_idx, font=(None, 12), fill="black", tag="show_id"+self.tag)


    def draw_bot(self, canvas, outer_col, eye_col, is_blue=True):
        direction = self.direction
        # set default direction, if we start from our initial position
        if direction is None:
            direction = 0 if is_blue else 180

        # ensure that our eyes are never on the bottom
        if direction == 0:
            flip = True
        else:
            flip = False

        # bot body
        canvas.create_arc(self.bounding_box(), start=rotate(20, direction), extent=320, style="pieslice",
                          width=0, outline=outer_col, fill=outer_col, tag = self.tag)

        # bot eye
        # first locate eye in the center
        eye_size = 0.15
        eye_box = (-eye_size - eye_size * 1j, eye_size + eye_size * 1j)
        # shift it to the middle of the bot just over the mouth
        eye_box = [item + 0.4 + 0.6j for item in eye_box]
        # take also care of flipping
        if flip:
            eye_box = [item.conjugate() for item in eye_box]
        # rotate based on direction
        eye_box = [cmath.exp(1j * math.radians(-direction)) * item for item in eye_box]
        eye_box = [self.screen((item.real, item.imag)) for item in eye_box]
        canvas.create_oval(eye_box, fill=eye_col, width=0, tag=self.tag)

    def draw(self, canvas, game_state):
        self.is_harvester = self.is_harvester_at(game_state['bots'][self.bot_id])

        if self.is_harvester:
            if self.team == 0:
                self.draw_bot(canvas, outer_col=BLUE, eye_col=YELLOW, is_blue=True)
            else:
                self.draw_bot(canvas, outer_col=RED, eye_col=YELLOW, is_blue=False)
        else:
            if self.team == 0:
                self.draw_destroyer(canvas, outer_col=BLUE, eye_col=YELLOW)
            else:
                self.draw_destroyer(canvas, outer_col=RED, eye_col=YELLOW)

    def draw_destroyer(self, canvas, outer_col, eye_col):
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
        if period == 0:
            y = [start[1] for x_i in x]
        else:
            y = [amplitude*math.cos(2*math.pi*(x_i-start[0])/period) + start[1] for x_i in x]
        # add container edges for the polygon
        x.insert(0, box_ll[0]); y.insert(0, box_ll[1] - 1)
        x.append(box_tr[0]); y.append(box_ll[1] - 1)
        canvas.create_polygon(list(zip(x,y)), width=1, outline=outer_col, fill=outer_col, tag=self.tag)

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
    def __init__(self, mesh, wall_neighbors=None, **kwargs):
        if wall_neighbors is None:
            self.wall_neighbors = []
        else:
            self.wall_neighbors = wall_neighbors

        super(Wall, self).__init__(mesh, **kwargs)


    def draw(self, canvas, game_state=None):
        scale = (self.mesh.half_scale_x + self.mesh.half_scale_y) * 0.6
        if not ((0, 1) in self.wall_neighbors or
                (1, 0) in self.wall_neighbors or
                (0, -1) in self.wall_neighbors or
                (-1, 0) in self.wall_neighbors):
            # if there is no direct neighbour, we can’t connect.
            # draw only a small dot.
            # TODO add diagonal lines
            canvas.create_line(self.screen((-0.3, 0)), self.screen((+0.3, 0)), fill=BROWN,
                               width=scale, tag=(self.tag, "wall"), capstyle="round")
        else:
            neighbours = [(-1, -1), (0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0)]
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if (dx, dy) in self.wall_neighbors:
                        if dx == dy == 0:
                            continue
                        if dx * dy != 0:
                            continue
                        index = neighbours.index((dx, dy))
                        if (neighbours[(index + 1) % len(neighbours)] in self.wall_neighbors and
                            neighbours[(index - 1) % len(neighbours)] in self.wall_neighbors):
                            pass
                        else:
                            canvas.create_line(self.screen((0, 0)), self.screen((2*dx, 2*dy)), fill=BROWN,
                                               width=scale, tag=(self.tag, "wall"), capstyle="round")

            # if we are drawing a closed square, fill in the internal part
            # detect the square when we are on the bottom-left vertex of it
            square_neighbors = {(0,0), (0,-1), (1,0),(1,-1)}
            if square_neighbors <= set(self.wall_neighbors):
                canvas.create_line(self.screen((1,0)), self.screen((1,-2)), fill=BROWN,
                                   width=scale, tag=(self.tag, "wall"))


class Food(TkSprite):
    @classmethod
    def food_pos_tag(cls, position):
        return "Food" + str(position)

    def draw(self, canvas, game_state=None):
        if self.position[0] < self.mesh.num_x/2:
            fill = BLUE
        else:
            fill = RED
        canvas.create_oval(self.bounding_box(0.4), fill=fill, width=0, tag=(self.tag, self.food_pos_tag(self.position), "food"))
