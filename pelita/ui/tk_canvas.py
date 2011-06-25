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


class Harvester(TkSprite):
    def draw(self, canvas):
        bounding_box = self.box()
        scale = self.scale

        direction = 110
        rot = lambda x: rotate(x, direction)

        canvas.create_arc(bounding_box, start=rot(30), extent=300, style="arc", width=0.2 * scale, outline=col(94, 158, 217), tag=self.tag)
        canvas.create_arc(bounding_box, start=rot(-20), extent=15, style="arc", width=0.2 * scale, outline=col(94, 158, 217), tag=self.tag)
        canvas.create_arc(bounding_box, start=rot(5), extent=15, style="arc", width=0.2 * scale, outline=col(94, 158, 217), tag=self.tag)

        canvas.create_arc(bounding_box, start=rot(-30), extent=10, style="arc", width=0.2 * scale, outline=col(235, 60, 60), tag=self.tag)
        canvas.create_arc(bounding_box, start=rot(20), extent=10, style="arc", width=0.2 * scale, outline=col(235, 60, 60), tag=self.tag)

        canvas.create_arc(bounding_box, start=rot(-5), extent=10, style="arc", width=0.2 * scale, outline=col(235, 235, 50), tag=self.tag)


class Destroyer(TkSprite):
    def draw(self, canvas):
        bounding_box = self.box()
        scale = self.scale

        direction = 110
        rot = lambda x: rotate(x, direction)

        canvas.create_arc(bounding_box, start=rot(30), extent=300, style="arc", width=0.2 * scale, outline=col(235, 90, 90), tag=self.tag)
        canvas.create_arc(bounding_box, start=rot(-20), extent=15, style="arc", width=0.2 * scale, outline=col(235, 90, 90), tag=self.tag)
        canvas.create_arc(bounding_box, start=rot(5), extent=15, style="arc", width=0.2 * scale, outline=col(235, 90, 90), tag=self.tag)

        canvas.create_arc(bounding_box, start=rot(-30), extent=10, style="arc", width=0.2 * scale, outline=col(94, 158, 217), tag=self.tag)
        canvas.create_arc(bounding_box, start=rot(20), extent=10, style="arc", width=0.2 * scale, outline=col(94, 158, 217), tag=self.tag)

        canvas.create_arc(bounding_box, start=rot(-5), extent=10, style="arc", width=0.2 * scale, outline=col(235, 235, 50), tag=self.tag)

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

    def translate_x(self, x):
        return self.offset_x + x * self.square_size[0]

    def translate_y(self, y):
        return self.offset_y + y * self.square_size[1]

    def draw_mesh(self, mesh):
        for position, item in mesh.iteritems():
            x, y = position
            self.draw_item(item, x, y)

    def draw_item(self, item, x, y):
        i = None
        if item == "c":
            i = Harvester(self.halfscale)
        if item == "o":
            i = Destroyer(self.halfscale)
        if item == "#":
            i = Wall(self.halfscale)
        if item == ".":
            i = Food(self.halfscale)
            dx = (i.x - i.position[0]) * self.width
            dy = (i.y - i.position[1]) * self.height
            i.move(self.canvas, dx, dy)

        if not i:
            return

        i.position = self.translate_x(x), self.translate_y(y)

        i.show()
        i.draw(self.canvas)


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
