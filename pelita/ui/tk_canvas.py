from Tkinter import *
from pelita.universe import CTFUniverse
from pelita.layout import Layout

def col(*rgb):
    return "#%02x%02x%02x" % rgb

def rotate(arc, rotation):
    return (arc + rotation) % 360

class TkSprite(object):
    def __init__(self):
        self.x = 0
        self.y = 0
        self.height = 10
        self.width = 10
        self.is_hidden = True

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

    @property
    def bounding_box(self):
        return self.box(1.0)

    def box(self, scale):
        return ((self.x) - self.width * scale, (self.y) - self.height * scale,
                (self.x) + self.width * scale, (self.y) + self.height * scale)

    @property
    def tag(self):
        return "tag" + str(id(self))

    def move(self, canvas, dx, dy):
        canvas.move(self.tag, dx, dy)


class Harvester(TkSprite):
    def draw(self, canvas):
        bounding_box = self.bounding_box

        direction = 110
        rot = lambda x: rotate(x, direction)

        canvas.create_oval(bounding_box, width=2, outline=col(94,158,217), tag=self.tag)
        canvas.create_arc(bounding_box, start=rot(-30), extent=10, style="arc", width=2, outline=col(235, 100, 100), tag=self.tag)
        canvas.create_arc(bounding_box, start=rot(20), extent=10, style="arc", width=2, outline=col(235, 100, 100), tag=self.tag)

        canvas.create_arc(bounding_box, start=rot(-5), extent=10, style="arc", width=2, outline=col(235, 235, 50), tag=self.tag)

class Wall(TkSprite):
    def draw(self, canvas):
        canvas.create_oval(self.box(0.3), fill=col(94,158,217), tag=self.tag)

class Food(TkSprite):
    def draw(self, canvas):
        canvas.create_oval(self.box(0.3), fill=col(217,158,158), tag=self.tag)

class UiCanvas(object):
    def __init__(self, x, y, width, height):
        self.mesh_width = x
        self.mesh_height = y
        self.width = width
        self.height = height

        self.square_size = (width / x, height / y)

        self.offset_x = self.square_size[0] / 2.0
        self.offset_y = self.square_size[1] / 2.0

        self.master = Tk()
        self.canvas = Canvas(self.master, width=width, height=height)
        self.canvas.pack()

    def draw_mesh(self, mesh):
        for position, item in mesh.iteritems():
            x = float(position[0]) / self.mesh_width
            y = float(position[1]) / self.mesh_height
            self.draw_item(item, x, y)

    def draw_item(self, item, x, y):
        i = None
        if item == "c":
            i = Harvester()
        if item == "o":
            i = Harvester()
        if item == "#":
            i = Wall()
        if item == ".":
            i = Food()

        if not i:
            return

        i.position = x * self.width + self.offset_x, y * self.height + self.offset_y
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
    canvas = UiCanvas(mesh.width, mesh.height, 300, 300)

    mesh[3,3] = "."

    canvas.draw_mesh(mesh)

    mainloop()
