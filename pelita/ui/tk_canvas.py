# -*- coding: utf-8 -*-

import Tkinter
import tkFont
import Queue

from .. import datamodel
from .tk_sprites import *
from ..utils.signal_handlers import wm_delete_window_handler

def guess_size(display_string, bounding_width, bounding_height, rel_size=0):
    no_lines = display_string.count("\n") + 1
    size_guess = bounding_height // ((3-rel_size) * no_lines)
    font = tkFont.Font(size=size_guess)
    text_width = font.measure(display_string)
    if text_width > bounding_width:
        font_size = size_guess * bounding_width // text_width
    else:
        font_size = size_guess
    return font_size


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
    def __init__(self, master, geometry=None):
        self.game_finish_overlay = lambda: None
        self.game_status_info = lambda: None

        self.mesh_graph = None
        self.geometry = geometry

        self.size_changed = True

        self.master = master
        self.canvas = None

        self.current_universe = None

    def init_canvas(self):
        self.score = Tkinter.Canvas(self.master.frame, width=self.mesh_graph.screen_width, height=30)
        self.score.config(background="white")
        self.score.pack(side=Tkinter.TOP, fill=Tkinter.X)

        self.status = Tkinter.Canvas(self.master.frame, width=self.mesh_graph.screen_width, height=25)
        self.status.config(background="white")
        self.status.pack(side=Tkinter.BOTTOM, fill=Tkinter.X)

        font_size = guess_size("QUIT",
                               self.mesh_graph.screen_width,
                               25,
                               rel_size = -1)

        Tkinter.Button(self.status,
                       font=(None, font_size),
                       foreground="black",
                       background="white",
                       justify=Tkinter.CENTER,
                       text="QUIT",
                       command=self.master.frame.quit).pack()

        self.canvas = Tkinter.Canvas(self.master.frame,
                                     width=self.mesh_graph.screen_width,
                                     height=self.mesh_graph.screen_height)
        self.canvas.config(background="white")
        self.canvas.pack(fill=Tkinter.BOTH, expand=Tkinter.YES)
        self.canvas.bind('<Configure>', self.resize)

    def update(self, universe, events, round=None, turn=None):
        # This method is called every now and then. Either when new information
        # about universe or events have arrived or when a resize has occurred.
        # Whenever new universe or event data is sent, this is fine, as every
        # drawing method will know how to deal with this information.
        # However, a call due to a simple resize will not include this information.
        # Therefore, we’d have to save this information in our class manually,
        # keeping track of updating the variables and hoping that no other
        # process starts relying on these attributes which are really meant to
        # be method-private. The alternative way we’re using here is following
        # the principle of least information:
        # Calls to the drawing methods are wrapped by a simple lambda, which
        # includes the last set of parameters given. This closure approach
        # allows us to hide the parameters from our interface and still be able
        # to use the most recent set of parameters when there is a mere resize.


        if universe and not self.canvas:
            if not self.mesh_graph:
                width = universe.maze.width
                height = universe.maze.height

                if self.geometry is None:
                    screensize = (
                        max(250, self.master.master.winfo_screenwidth() - 100),
                        max(250, self.master.master.winfo_screenheight() - 100)
                        )
                else:
                    screensize = self.geometry
                scale_x = screensize[0] / width
                scale_y = screensize[1] / height
                scale = int(min(scale_x, scale_y, 50))
                self.mesh_graph = MeshGraph(width, height, scale * width, scale * height)

                self.bot_sprites = {}

            self.init_canvas()
            self.init_bots(universe)

        if not universe and not self.current_universe:
            return

        if not universe and not self.size_changed:
            return

        if universe:
            self.current_universe = universe

        if round is not None and turn is not None:
            self.game_status_info = lambda: self.draw_status_info(turn, round)
        self.game_status_info()

        self.draw_universe(self.current_universe)

        if events:
            for team_wins in events.filter_type(datamodel.TeamWins):
                team_index = team_wins.winning_team_index
                team_name = universe.teams[team_index].name
                self.game_finish_overlay = lambda: self.draw_game_over(team_name)
            for game_draw in events.filter_type(datamodel.GameDraw):
                self.game_finish_overlay = lambda: self.draw_game_draw()

        self.game_finish_overlay()


    def draw_universe(self, universe):
        self.mesh_graph.num_x = universe.maze.width
        self.mesh_graph.num_y = universe.maze.height

        self.draw_background(universe)
        self.draw_maze(universe)
        self.draw_food(universe)

        self.draw_title(universe)
        self.draw_bots(universe)

        self.size_changed = False

    def draw_background(self, universe):
        """ Draws a line between blue and red team.
        """
        if not self.size_changed:
            return
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
        left_team = "%s %d " % (universe.teams[0].name, universe.teams[0].score)
        right_team = " %d %s" % (universe.teams[1].score, universe.teams[1].name)
        font_size = guess_size(left_team+':'+right_team,
                               self.mesh_graph.screen_width,
                               30,
                               rel_size = +1)

        self.score.create_text(center, 15, text=left_team, font=(None, font_size), fill=col(94, 158, 217), tag="title", anchor=Tkinter.E)

        self.score.create_text(center, 15, text=":", font=(None, font_size), tag="title", anchor=Tkinter.CENTER)

        self.score.create_text(center+2, 15, text=right_team, font=(None, font_size), fill=col(235, 90, 90), tag="title", anchor=Tkinter.W)

    def draw_status_info(self, turn, round):
        self.status.delete("roundturn")
        roundturn = "Bot %d, Round %d   " % (turn, round)
        font_size = guess_size(roundturn,
                               self.mesh_graph.screen_width,
                               25,
                               rel_size = 0)

        self.status.create_text(self.mesh_graph.screen_width, 25,
                                anchor=Tkinter.SE,
                                text=roundturn, font=(None, font_size), tag="roundturn")

    def draw_end_of_game(self, display_string):
        """ Draw an end of game string. """
        self.canvas.delete("gameover")

        center = (self.mesh_graph.screen_width // 2,
                  self.mesh_graph.screen_height //2)

        font_size = guess_size(display_string,
                               self.mesh_graph.screen_width,
                               self.mesh_graph.screen_height,
                               rel_size = +1)

        for i in [-2, -1, 0, 1, 2]:
            for j in [-2, -1, 0, 1, 2]:
                self.canvas.create_text(center[0] - i, center[1] - j,
                        text=display_string,
                        font=(None, font_size, "bold"),
                        fill="#ED1B22", tag="gameover",
                        justify=Tkinter.CENTER, anchor=Tkinter.CENTER)

        self.canvas.create_text(center[0] , center[1] ,
                text=display_string,
                font=(None, font_size, "bold"),
                fill="#FFC903", tag="gameover",
                justify=Tkinter.CENTER, anchor=Tkinter.CENTER)


    def draw_game_over(self, win_name):
        """ Draw the game over string. """
        # shorten the winning name
        plural = '' if win_name.endswith('s') else 's'
        if len(win_name) > 25:
            win_name = win_name[:22] + '...'
        self.draw_end_of_game(u"GAME OVER\n%s win%s!" % (win_name, plural))

    def draw_game_draw(self):
        """ Draw the game draw string. """
        self.draw_end_of_game("GAME OVER\nDRAW!")

    def clear(self):
        self.canvas.delete(Tkinter.ALL)

    def resize(self, event):
        # need to be careful not to get negative numbers
        # Tk will crash, if it receives negative numbers
        if event.height > 0:
            self.mesh_graph.screen_width = event.width
            self.mesh_graph.screen_height = event.height
        self.size_changed = True

    def draw_food(self, universe):
        self.canvas.delete("food")
        for position, items in universe.maze.iteritems():
            model_x, model_y = position
            if datamodel.Food in items:
                food_item = Food(self.mesh_graph, model_x, model_y)
                food_item.draw(self.canvas)

    def draw_maze(self, universe):
        if not self.size_changed:
            return
        self.canvas.delete("wall")
        for position, items in universe.maze.iteritems():
            model_x, model_y = position
            if datamodel.Wall in items:
                wall_item = Wall(self.mesh_graph, model_x, model_y)
                wall_item.wall_neighbours = []
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        try:
                            if datamodel.Wall in universe.maze[model_x + dx, model_y + dy]:
                                wall_item.wall_neighbours.append( (dx, dy) )
                        except IndexError:
                            pass
                wall_item.draw(self.canvas)

    def init_bots(self, universe):
        for bot in universe.bots:
            bot_sprite = BotSprite(self.mesh_graph, team=bot.team_index, bot_idx=bot.index)

            self.bot_sprites[bot.index] = bot_sprite
            bot_sprite.position = bot.current_pos

    def draw_bots(self, universe):
        for bot_idx, bot_sprite in self.bot_sprites.iteritems():
            bot_sprite.position = universe.bots[bot_sprite.bot_idx].current_pos

            bot_sprite.redraw(self.canvas, universe)


class TkApplication(object):
    def __init__(self, queue, geometry=None, master=None):
        self.master = master
        self.frame = Tkinter.Frame(self.master)
        self.master.title("Pelita")

        self.queue = queue

        self.frame.pack(fill=Tkinter.BOTH, expand=Tkinter.YES)

        self.ui_canvas = UiCanvas(self, geometry=geometry)

        self.master.protocol("WM_DELETE_WINDOW", wm_delete_window_handler)

    def read_queue(self, event=None):
        try:
            # read all events.
            # if queue is empty, try again in 50 ms
            # we don’t want to block here and lock
            # Tk animations
            while True:
                observed = self.queue.get(False)
                self.observe(observed)

                if not event:
                    self.master.after(1, self.read_queue)
                return
        except Queue.Empty:
            self.observe({})
            if not event:
                self.master.after(1, self.read_queue)

    def observe(self, observed):
        universe = observed.get("universe")
        events = observed.get("events")
        round = observed.get("round")
        turn = observed.get("turn")

        self.ui_canvas.update(universe, events, round, turn)

    def on_quit(self):
        """ override for things which must be done when we exit.
        """
        pass

    def quit(self):
        self.on_quit()
        Tkinter.Frame.quit(self)
