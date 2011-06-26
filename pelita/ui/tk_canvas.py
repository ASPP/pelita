from Tkinter import *
from pelita.universe import CTFUniverse
from pelita.layout import Layout

def col(*rgb):
    return "#%02x%02x%02x" % rgb

def rotate(arc, rotation):
    return (arc + rotation) % 360

class TkSprite(object):
    def __init__(self, scale):
        self.x = 0
        self.y = 0
        self.height = 1
        self.width = 1
        self.is_hidden = True

        self.scale = scale

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

    def draw(self):
        pass

    def box(self, factor=1.0):
        return ((self.x) - self.width * factor * self.scale, (self.y) - self.height * factor * self.scale,
                (self.x) + self.width * factor * self.scale, (self.y) + self.height * factor * self.scale)

    @property
    def tag(self):
        return "tag" + str(id(self))

    def move(self, canvas, dx, dy):
        canvas.move(self.tag, dx, dy)

class BotSprite(TkSprite):
    def draw_bot(self, canvas, outer_col, eye_col, central_col=col(235, 235, 50)):

        bounding_box = self.box()
        scale = self.scale

        direction = 110
        rot = lambda x: rotate(x, direction)

        canvas.create_arc(bounding_box, start=rot(30), extent=300, style="arc", width=0.2 * scale, outline=outer_col, tag=self.tag)
        canvas.create_arc(bounding_box, start=rot(-20), extent=15, style="arc", width=0.2 * scale, outline=outer_col, tag=self.tag)
        canvas.create_arc(bounding_box, start=rot(5), extent=15, style="arc", width=0.2 * scale, outline=outer_col, tag=self.tag)

        canvas.create_arc(bounding_box, start=rot(-30), extent=10, style="arc", width=0.2 * scale, outline=eye_col, tag=self.tag)
        canvas.create_arc(bounding_box, start=rot(20), extent=10, style="arc", width=0.2 * scale, outline=eye_col, tag=self.tag)

        canvas.create_arc(bounding_box, start=rot(-5), extent=10, style="arc", width=0.2 * scale, outline=central_col, tag=self.tag)

        score = 2
        canvas.create_text(self.x, self.y, text=score, font=(None, int(0.5 * self.scale)))


class Harvester(BotSprite):
    def draw(self, canvas):
        self.draw_bot(canvas, outer_col=col(94, 158, 217), eye_col=col(235, 60, 60))

class Destroyer(BotSprite):
    def draw(self, canvas):
        self.draw_bot(canvas, outer_col=col(235, 90, 90), eye_col=col(94, 158, 217))
        self.draw_polygon(canvas)

    def draw_polygon(self, canvas):
        direction = 110

        penta_arcs = range(0 - direction, 360 - direction, 360 / 5)
        penta_arcs_inner = [arc + 360 / 5 / 2.0 for arc in penta_arcs]

        import cmath, math

        coords = []
        for a, i in zip(penta_arcs, penta_arcs_inner):
            # we rotate with the help of complex numbers
            n = cmath.rect(self.scale * 0.85, a * math.pi / 180.0)
            coords.append((n.real + self.x, n.imag + self.y))
            n = cmath.rect(self.scale * 0.3, i * math.pi / 180.0)
            coords.append((n.real + self.x, n.imag + self.y))

        canvas.create_polygon(width=0.05 * self.scale, fill="", outline=col(94, 158, 217), *coords)

class Wall(TkSprite):
    def draw(self, canvas):
        canvas.create_oval(self.box(0.3), fill=col(94, 158, 217), tag=self.tag)

class Food(TkSprite):
    def draw(self, canvas):
        canvas.create_oval(self.box(0.3), fill=col(217, 158, 158), tag=self.tag)

class UiCanvas(object):
    def __init__(self, x, y, scale):
        self.mesh_width = x
        self.mesh_height = y

        self.scale = float(scale)
        self.halfscale = float(scale) / 2

        self.width = x * scale
        self.height = y * scale

        self.square_size = (scale, scale)

        self.offset_x = self.halfscale
        self.offset_y = self.halfscale

        self.master = Tk()
        self.canvas = Canvas(self.master, width=self.width, height=self.height)
        self.canvas.pack()

        self.registered_items = []
        self.mapping = {
            "c": Harvester,
            "o": Destroyer,
            "#": Wall,
            ".": Food
        }

    def translate_x(self, x):
        return self.offset_x + x * self.square_size[0]

    def translate_y(self, y):
        return self.offset_y + y * self.square_size[1]

    def draw_mesh(self, mesh):
        for position, char in mesh.iteritems():
            x, y = position
            self.draw_item(char, x, y)

    def draw_item(self, char, x, y):
        item_class = self.mapping.get(char)
        if not item_class:
            return

        item = item_class(self.halfscale)
        self.registered_items.append(item)

        item.position = self.translate_x(x), self.translate_y(y)

        item.show()
        item.draw(self.canvas)


if __name__ == "__main__":

    test_layout = (
            """ ########
                #c     #
                #  .   #
                #    o #
                ######## """)

    mesh = CTFUniverse(Layout.strip_layout(test_layout), 0).mesh
    canvas = UiCanvas(mesh.width, mesh.height, 60)

    mesh[3,3] = "."

    canvas.draw_mesh(mesh)

    mainloop()
