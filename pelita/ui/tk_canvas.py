# -*- coding: utf-8 -*-

import Tkinter
import Queue

from pelita import datamodel
from pelita.ui.tk_sprites import *
from pelita.utils.signal_handlers import wm_delete_window_handler

class MeshGraph(object):
    """ A `MeshGraph` is a structure of `mesh_width` * `mesh_height` rectangles,
    covering an area of `screen_width`, `screen_height`.
    """
    def __init__(self, mesh_width, mesh_height, screen_width, screen_height):
        self.mesh_width = mesh_width
        self.mesh_height = mesh_height
        self.screen_height = screen_height
        self.screen_width = screen_width

    @property
    def rect_width(self):
        """ The width of a single field.
        """
        return float(self.screen_width) / self.mesh_width

    @property
    def rect_height(self):
        """ The height of a single field.
        """
        return float(self.screen_height) / self.mesh_height

    @property
    def half_scale_x(self):
        return self.rect_width / 2.0

    @property
    def half_scale_y(self):
        return self.rect_height / 2.0

    def mesh_trafo(self, mesh_x, mesh_y):
        return Trafo(self, mesh_x, mesh_y)

    def mesh_to_screen(self, mesh, coords):
        mesh_x, mesh_y = mesh
        coords_x, coords_y = coords

        real_x = self.mesh_to_screen_x(mesh_x, coords_x)
        real_y = self.mesh_to_screen_y(mesh_y, coords_y)
        return (real_x, real_y)

    def mesh_to_screen_x(self, mesh_x, model_x):
        # coords are between -1 and +1: shift on [0, 1]
        trafo_x = (model_x + 1.0) / 2.0

        real_x = self.rect_width * (mesh_x + trafo_x)
        return real_x

    def mesh_to_screen_y(self, mesh_y, model_y):
        # coords are between -1 and +1: shift on [0, 1]
        trafo_y = (model_y + 1.0) / 2.0

        real_y = self.rect_height * (mesh_y + trafo_y)
        return real_y

    def __repr__(self):
        return "MeshGraph(%d, %d, %d, %d)" % (self.mesh_width, self.mesh_height,
                                              self.screen_width, self.screen_height)

class Trafo(object):
    def __init__(self, mesh_graph, mesh_x, mesh_y):
        self.mesh_graph = mesh_graph
        self.mesh_x = mesh_x
        self.mesh_y = mesh_y

    def screen_x(self, model_x):
        return self.mesh_graph.mesh_to_screen_x(self.mesh_x, model_x)

    def screen_y(self, model_y):
        return self.mesh_graph.mesh_to_screen_y(self.mesh_y, model_y)

    def screen(self, model_x, model_y):
        return self.mesh_graph.mesh_to_screen((self.mesh_x, self.mesh_y), (model_x, model_y))



class UiCanvas(object):
    def __init__(self, master):
        self.mesh_graph = None

        self.size_changed = True

        self.master = master
        self.canvas = None

        self.registered_items = []
        self.mapping = {
            datamodel.Wall: Wall,
            datamodel.Food: Food
        }

        self.current_universe = None
        self.previous_universe = None

    def init_canvas(self):
        self.score = Tkinter.Canvas(self.master.frame, width=self.mesh_graph.screen_width, height=30)
        self.score.config(background="white")
        self.score.pack()

        self.canvas = Tkinter.Canvas(self.master.frame, width=self.mesh_graph.screen_width, height=self.mesh_graph.screen_height)
        self.canvas.config(background="white")
        self.canvas.pack(fill=Tkinter.BOTH, expand=Tkinter.YES)
        self.canvas.bind('<Configure>', self.resize)

        self.status = Tkinter.Canvas(self.master.frame, width=self.mesh_graph.screen_width, height=25)
        self.status.config(background="white")
        self.status.pack(side=Tkinter.BOTTOM, fill=Tkinter.X)

    def update(self, events, universe, round=None, turn=None):
        if not self.canvas:
            if not self.mesh_graph:
                width = universe.maze.width
                height = universe.maze.height

                screensize = (
                    max(250, self.master.master.winfo_screenwidth() - 60),
                    max(250, self.master.master.winfo_screenheight() - 60)
                )
                scale_x = screensize[0] / width
                scale_y = screensize[1] / height

                scale = int(min(scale_x, scale_y, 50))
                self.mesh_graph = MeshGraph(width, height, scale * width, scale * height)

                self.bot_sprites = {}

            self.init_canvas()
            self.init_bots(universe)

        self.previous_universe = self.current_universe
        self.current_universe = universe

        if round is not None and turn is not None:
            self.status.delete("roundturn")
            roundturn = "Bot %d, Round %d   " % (turn, round)
            self.status.create_text(self.mesh_graph.screen_width, 25,
                                    anchor=Tkinter.SE,
                                    text=roundturn, font=(None, 15), tag="roundturn")

        if not self.previous_universe:
            self.draw_universe(self.current_universe)
        else:
            self.draw_universe(self.previous_universe)

        if events:
            for team_wins in events.filter_type(datamodel.TeamWins):
                team_index = team_wins.winning_team_index
                team_name = universe.teams[team_index].name
                self.draw_game_over(team_name)

    def draw_universe(self, universe):
        self.mesh_graph.num_x = universe.maze.width
        self.mesh_graph.num_y = universe.maze.height

        if self.size_changed:
            self.clear()

            self.draw_background(universe)
            self.draw_mesh(universe.maze)
            self.size_changed = False

        self.draw_title(universe)
        self.draw_bots(universe)

    def draw_background(self, universe):
        self.canvas.delete("background")

        center = self.mesh_graph.screen_width // 2
        cols = (col(94, 158, 217), col(235, 90, 90), col(80, 80, 80))

        scale = self.mesh_graph.half_scale_x * 0.2

        for color, x_orig in zip(cols, (center - 3, center + 3, center)):
            x_width = self.mesh_graph.half_scale_x // 4

            x_prev = None
            y_prev = None
            for y in range((self.mesh_graph.mesh_height -1 )* 10):
                x_real = x_orig + x_width * math.sin(y * 10)
                y_real = self.mesh_graph.mesh_to_screen_y(y / 10.0, 0)
                if x_prev and y_prev:
                    self.canvas.create_line((x_prev, y_prev, x_real, y_real), width=scale, fill=color, tag="background")
                x_prev, y_prev = x_real, y_real

    def draw_title(self, universe):
        self.score.delete("title")
        center = self.mesh_graph.screen_width // 2

        left_team = "%s %d" % (universe.teams[0].name, universe.teams[0].score)
        self.score.create_text(center - 10, 15, text=left_team, font=(None, 25), fill=col(94, 158, 217), tag="title", anchor=Tkinter.E)

        self.score.create_text(center, 15, text=":", font=(None, 25), tag="title", anchor=Tkinter.CENTER)

        right_team = "%d %s" % (universe.teams[1].score, universe.teams[1].name)
        self.score.create_text(center + 10, 15, text=right_team, font=(None, 25), fill=col(235, 90, 90), tag="title", anchor=Tkinter.W)

    def draw_game_over(self, win_name):
        center = self.mesh_graph.screen_width // 2, self.mesh_graph.screen_height //2
        self.canvas.create_text(center[0], center[1], text="GAME OVER\nTeam \"%s\" wins!"%win_name, font=(None, 60, "bold"), fill="red", tag="gameover",
                                justify=Tkinter.CENTER, anchor=Tkinter.CENTER)
        text = Tkinter.Button(self.status, font=(None, 10), foreground="black", background="white",
                              justify=Tkinter.CENTER, text="QUIT", command=self.master.quit).pack()

    def clear(self):
        self.canvas.delete(Tkinter.ALL)

    def resize(self, event):
        # need to be careful not to get negative numbers
        # Tk will crash, if it receives negative numbers
        if event.height > 0:
            self.mesh_graph.screen_width = event.width
            self.mesh_graph.screen_height = event.height
        self.size_changed = True

    def draw_mesh(self, mesh):
        for position, items in mesh.iteritems():
            x, y = position
            self.draw_items(items, x, y, mesh)

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

    def draw_items(self, items, x, y, mesh):
        item_class = None
        for item in items:
            for key in self.mapping:
                if issubclass(key, item):
                    item_class = self.mapping[key]

        if not item_class:
            return

        item = item_class(self.mesh_graph)
        self.registered_items.append(item)

        if isinstance(item, Wall):
            item.wall_neighbours = []
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    try:
                        if datamodel.Wall in mesh[x + dx, y + dy]:
                            item.wall_neighbours.append( (dx, dy) )
                    except IndexError:
                        pass
        item.position = x, y

        item.redraw(self.canvas)

class TkApplication(object):
    def __init__(self, queue, master=None):
        self.master = master
        self.frame = Tkinter.Frame(self.master)
        self.master.title("Pelita")

        self.queue = queue

        self.frame.pack(fill=Tkinter.BOTH, expand=Tkinter.YES)

        self.ui_canvas = UiCanvas(self)

        self.master.protocol("WM_DELETE_WINDOW", wm_delete_window_handler)

    def read_queue(self):
        try:
            # read all events.
            # if queue is empty, try again in 50 ms
            # we don’t want to block here and lock
            # Tk animations
            while True:
                observed = self.queue.get(False)
                self.observe(observed)

                self.master.after(50, self.read_queue)
                return
        except Queue.Empty:
            self.master.after(50, self.read_queue)

    def observe(self, observed):
        round = observed.get("round")
        turn = observed.get("turn")
        universe = observed["universe"]
        events = observed.get("events")

        self.ui_canvas.update(events, universe, round, turn)

    def on_quit(self):
        """ override for things which must be done when we exit.
        """
        pass

    def quit(self):
        self.on_quit()
        Tkinter.Frame.quit(self)
