import json
import logging
import time

import zmq

import tkinter
import tkinter.font

from ..game import next_round_turn
from ..player.team import _ensure_list_tuples
from .tk_sprites import BotSprite, Food, Wall, Arrow, RED, BLUE, YELLOW, GREY, BROWN, LIGHT_BLUE, LIGHT_RED, STRONG_BLUE, STRONG_RED
from .tk_utils import wm_delete_window_handler
from .. import layout

_logger = logging.getLogger(__name__)


def guess_size(display_string, bounding_width, bounding_height, rel_size=0):
    no_lines = display_string.count("\n") + 1
    size_guess = bounding_height // ((3-rel_size) * no_lines)
    font = tkinter.font.Font(size=size_guess)
    text_width = font.measure(display_string)
    if text_width > bounding_width:
        font_size = size_guess * bounding_width // text_width
    else:
        font_size = size_guess
    return font_size

class MeshGraph:
    """ A `MeshGraph` is a structure of `mesh_width` * `mesh_height` rectangles,
    covering an area of `screen_width`, `screen_height`.
    """
    def __init__(self, mesh_width, mesh_height, screen_width, screen_height):
        self.mesh_width = mesh_width
        self.mesh_height = mesh_height
        self.screen_height = screen_height
        self.screen_width = screen_width
        self.padding = 10

    @property
    def rect_width(self):
        """ The width of a single field.
        """
        # we have to adjust by one pixel for the border
        width = float(self.screen_width - 1 - 2 * self.padding) / self.mesh_width
        # if the UI is not initialized yet (or just really really small) this may
        # result in a negative value. Ensure that it is always positive or zero.
        if width < 0:
            width = 0.0
        return width

    @property
    def rect_height(self):
        """ The height of a single field.
        """
        # we have to adjust by one pixel for the border
        height = float(self.screen_height - 1 - 2 * self.padding) / self.mesh_height
        # if the UI is not initialized yet (or just really really small) this may
        # result in a negative value. Ensure that it is always positive or zero.
        if height < 0:
            height = 0.0
        return height

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

        real_x = self.rect_width * (mesh_x + trafo_x) + self.padding
        return real_x

    def mesh_to_screen_y(self, mesh_y, model_y):
        # coords are between -1 and +1: shift on [0, 1]
        trafo_y = (model_y + 1.0) / 2.0

        real_y = self.rect_height * (mesh_y + trafo_y) + self.padding
        return real_y

    def screen_to_mesh_coord(self, screen_x, screen_y):
        # returns the mesh coordinate of the selected screen coordinate
        # or None, when it is outside of the mesh

        x = int((screen_x - self.padding) / self.rect_width)
        y = int((screen_y - self.padding) / self.rect_height)

        if not 0 <= x < self.mesh_width or not 0 <= y < self.mesh_height:
            return None
        return (x, y)

    def __repr__(self):
        return "MeshGraph(%d, %d, %d, %d)" % (self.mesh_width, self.mesh_height,
                                              self.screen_width, self.screen_height)

class Trafo:
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

class UI:
    pass

class TkApplication:
    def __init__(self, master, controller_address=None,
                 geometry=None, delay=1, stop_after=None):
        self.master = master
        self.master.configure(background="white")

        self.context = zmq.Context()

        if controller_address:
            self.controller_socket = self.context.socket(zmq.DEALER)
            self.controller_socket.connect(controller_address)
        else:
            self.controller_socket = None

        self.master.title("Pelita")

        self.game_finish_overlay = lambda: None

        self.mesh_graph = None
        self.geometry = geometry

        self._default_font = tkinter.font.nametofont("TkDefaultFont")
        self._default_font_size = self._default_font.cget('size')

        self.size_changed = True

        self._grid_enabled = False

        self._times = []
        self._fps = None
        self.selected = None

        self.game_uuid = None
        self.bot_sprites = {}
        self.shadow_sprites = {}

        self._universe = None
        self._game_state = None

        self.ui = UI()

        self.ui.header_canvas = tkinter.Canvas(master, height=50)
        self.ui.header_canvas.config(background="white", bd=0, highlightthickness=0, relief='ridge')

        self.ui.sub_header = tkinter.Frame(master, height=25)
        self.ui.sub_header.config(background="white")

        self.ui.status_canvas = tkinter.Frame(master, height=25)
        self.ui.status_canvas.config(background="white")

        self.ui.game_canvas = tkinter.Canvas(master)
        self.ui.game_canvas.config(background="white", bd=0, highlightthickness=0, relief='ridge')
        self.ui.game_canvas.bind('<Configure>', lambda e: master.after_idle(self.update))
        self.ui.game_canvas.bind('<Button-1>', self.on_click)

        self.ui.status_00 = tkinter.Frame(self.ui.status_canvas, background="white", padx=5, pady=0)
        self.ui.status_01 = tkinter.Frame(self.ui.status_canvas, background="white", padx=5, pady=0)
        self.ui.status_02 = tkinter.Frame(self.ui.status_canvas, background="white", padx=5, pady=0)
        self.ui.status_10 = tkinter.Frame(self.ui.status_canvas, background="white", padx=5, pady=0)
        self.ui.status_11 = tkinter.Frame(self.ui.status_canvas, background="white", padx=5, pady=0)
        self.ui.status_12 = tkinter.Frame(self.ui.status_canvas, background="white", padx=5, pady=0)
        self.ui.status_20 = tkinter.Frame(self.ui.status_canvas, background="white", padx=5, pady=0)
        self.ui.status_21 = tkinter.Frame(self.ui.status_canvas, background="white", padx=5, pady=0)
        self.ui.status_22 = tkinter.Frame(self.ui.status_canvas, background="white", padx=5, pady=0)

        self.ui.status_00.grid(row=0, column=0, sticky="W")
        self.ui.status_01.grid(row=0, column=1, sticky="WE")
        self.ui.status_02.grid(row=0, column=2, sticky="E")
        self.ui.status_10.grid(row=1, column=0, sticky="W")
        self.ui.status_11.grid(row=1, column=1, columnspan=2, sticky="E")
#        self.ui.status_12.grid(row=1, column=2, sticky="E")
        self.ui.status_20.grid(row=2, column=0, sticky="W")
        self.ui.status_21.grid(row=2, column=1, sticky="W")
        self.ui.status_22.grid(row=2, column=2, sticky="E")

        self.ui.status_canvas.grid_columnconfigure(0, weight=1, uniform='status')
        self.ui.status_canvas.grid_columnconfigure(1, weight=1, uniform='status')
        self.ui.status_canvas.grid_columnconfigure(2, weight=1, uniform='status')

        self.ui.button_game_speed_slower = tkinter.Button(self.ui.status_10,
            foreground="black",
            background="white",
            justify=tkinter.CENTER,
            text="slower",
            padx=12,
            command=self.delay_inc)
        self.ui.button_game_speed_slower.pack(side=tkinter.LEFT)

        self.ui.button_game_speed_faster = tkinter.Button(self.ui.status_10,
            foreground="black",
            background="white",
            justify=tkinter.CENTER,
            text="faster",
            padx=12,
            command=self.delay_dec)
        self.ui.button_game_speed_faster.pack(side=tkinter.LEFT)

        self._check_speed_button_state()

        self.ui.button_game_toggle_grid = tkinter.Button(self.ui.status_10,
            foreground="black",
            background="white",
            justify=tkinter.CENTER,
            padx=12,
            command=self.toggle_grid)
        self.ui.button_game_toggle_grid.pack(side=tkinter.LEFT)

        self._check_grid_toggle_state()

        self.ui.status_fps_info = tkinter.Label(self.ui.status_20,
            text="",
            font=(None, 8),
            foreground="black",
            background="white",
            justify=tkinter.CENTER)
        self.ui.status_fps_info.pack(side=tkinter.LEFT)

        self.ui.status_selected = tkinter.Label(self.ui.status_22,
            text="",
            font=(None, 8),
            foreground="black",
            background="white",
            justify=tkinter.CENTER)
        self.ui.status_selected.pack(side=tkinter.RIGHT)

        tkinter.Button(self.ui.status_00,
                       foreground="black",
                       background="white",
                       justify=tkinter.CENTER,
                       text="PLAY/PAUSE",
                       padx=12,
                       command=self.toggle_running).pack(side=tkinter.LEFT, expand=tkinter.YES)

        tkinter.Button(self.ui.status_00,
                       foreground="black",
                       background="white",
                       justify=tkinter.CENTER,
                       text="STEP",
                       padx=12,
                       command=self.request_step).pack(side=tkinter.LEFT, expand=tkinter.YES)

        tkinter.Button(self.ui.status_00,
                       foreground="black",
                       background="white",
                       justify=tkinter.CENTER,
                       text="ROUND",
                       padx=12,
                       command=self.request_round).pack(side=tkinter.LEFT, expand=tkinter.YES)

        tkinter.Button(self.ui.status_01,
                       foreground="black",
                       background="white",
                       justify=tkinter.CENTER,
                       text="QUIT",
                       width=30,
                       padx=12,
                       command=self.quit).pack(side=tkinter.TOP, fill=tkinter.BOTH, anchor=tkinter.CENTER)

        # Add circles to show which bot is active.
        self.ui.bot_traffic_lights_canvas = tkinter.Canvas(self.ui.status_02, height=25, width=44,
                                                           background="white", bd=0, highlightthickness=0,
                                                           relief='ridge')
        self.ui.bot_traffic_lights_canvas.pack(side=tkinter.LEFT)
        self.ui.bot_traffic_lights_c = []
        for idx in range(4):
            spacing = 10
            x0, y0 = 2.5 + idx * spacing, 13
            circle = self.ui.bot_traffic_lights_canvas.create_text(x0, y0, text=layout.BOT_I2N[idx], font=(None, 11), fill="black")
            self.ui.bot_traffic_lights_c.append(circle)

        self.ui.status_round_info = tkinter.Label(self.ui.status_02, text="", background="white")
        self.ui.status_round_info.pack(side=tkinter.LEFT)

        self.ui.status_layout_info = tkinter.Label(self.ui.status_11, text="", background="white")
        self.ui.status_layout_info.pack(side=tkinter.LEFT)

        self.ui.header_canvas.pack(side=tkinter.TOP, fill=tkinter.BOTH)
#        self.ui.sub_header.pack(side=tkinter.TOP, fill=tkinter.BOTH)
        self.ui.status_canvas.pack(side=tkinter.BOTTOM, fill=tkinter.BOTH)
        self.ui.game_canvas.pack(side=tkinter.TOP, fill=tkinter.BOTH, expand=tkinter.YES)#fill=tkinter.BOTH, expand=tkinter.YES)

        self._min_delay = 1
        self._delay = delay
        self._stop_after = stop_after
        self._stop_after_delay = delay
        if self._stop_after is not None:
            self._delay = self._min_delay

        self._check_speed_button_state()

        self._observed_steps = set()

        self.running = True

        self.master.bind('q', lambda event: self.quit())
        self.master.bind('<numbersign>', lambda event: self.toggle_grid())
        self.master.bind('<greater>', lambda event: self.delay_dec())
        self.master.bind('<less>', lambda event: self.delay_inc())
        self.master.bind('<space>', lambda event: self.toggle_running())
        self.master.bind('<Return>', lambda event: self.request_step())
        self.master.bind('<Shift-Return>', lambda event: self.request_round())
        self.master.createcommand('exit', self.quit)
        self.master.protocol("WM_DELETE_WINDOW", self.quit)

        if self.controller_socket:
            self.master.after_idle(self.request_initial)


    def init_mesh(self, game_state):
        width, height = game_state['shape']

        if self.geometry is None:
            screensize = (
                max(250, self.master.winfo_screenwidth() - 100),
                max(250, self.master.winfo_screenheight() - 100)
                )
        else:
            screensize = self.geometry
        scale_x = screensize[0] / width
        scale_y = screensize[1] / height
        scale = int(min(scale_x, scale_y, 50))

        self.mesh_graph = MeshGraph(width, height, scale * width, scale * height)
        self.init_bot_sprites(game_state['bots'])

    def update(self, game_state=None):
        # Update the times for the fps calculation (if we are running)
        # Our fps is only relevant for how often the bots update our viewer.
        # When the viewer updates itself, we do not count it.
        if self.running and game_state:
            self._times.append(time.monotonic())
            if len(self._times) > 3:
                # take the mean of the last two time differences
                # this could also be improved by taking up to four if available
                try:
                    self._fps = 2 / ((self._times[-1] - self._times[-2]) + (self._times[-2] - self._times[-3]))
                except ZeroDivisionError:
                    self._fps = 1 / 0.001
            else:
                self._fps = None
            if len(self._times) > 100:
                # Garbage collect old times
                self._times = self._times[-3:]

        if game_state is not None:
            self._game_state = game_state
        game_state = self._game_state
        if not game_state:
            return

        #if game_state['game_uuid'] != self.game_uuid:
        if not self.game_uuid:
            #self.game_uuid = game_state['game_uuid']
            self.game_uuid = 1
            self.init_mesh(game_state)

        if ((self.mesh_graph.screen_width, self.mesh_graph.screen_height)
            != (self.ui.game_canvas.winfo_width(), self.ui.game_canvas.winfo_height())):
            self.size_changed = True

        self.mesh_graph.screen_width = self.ui.game_canvas.winfo_width()
        self.mesh_graph.screen_height = self.ui.game_canvas.winfo_height()

        if self.mesh_graph.screen_width < 600:
            if self._default_font.cget('size') != 8:
                self._default_font.configure(size=8)
        else:
            if self._default_font.cget('size') != self._default_font_size:
                self._default_font.configure(size=self._default_font_size)

        self.draw_universe(game_state)

        eaten_food = []
        for food_pos, food_item in self.food_items.items():
            if not food_pos in game_state["food"]:
                self.ui.game_canvas.delete(food_item.tag)
                eaten_food.append(food_pos)
        for food_pos in eaten_food:
            del self.food_items[food_pos]

        winning_team_idx = game_state.get("whowins")
        if winning_team_idx is None:
            self.draw_end_of_game(None)
        elif winning_team_idx in (0, 1):
            team_name = game_state["team_names"][winning_team_idx]
            self.draw_game_over(team_name)
        elif winning_team_idx == 2:
            self.draw_game_draw()

        self.size_changed = False

    def draw_universe(self, game_state):
        self.mesh_graph.num_x = game_state['shape'][0]
        self.mesh_graph.num_y = game_state['shape'][1]

        self.draw_grid()
        self.draw_selected(game_state)
        self.draw_line_of_sight(game_state)
        self.draw_background()
        self.draw_maze(game_state)
        self.draw_food(game_state)

        self.draw_title(game_state)
        self.draw_shadow_bots(game_state)
        self.draw_bots(game_state)

        self.draw_moves(game_state)

        self.draw_status_info(game_state)

    def draw_grid(self):
        """ Draws a light grid on the background.
        """
        if not self.size_changed:
            return
        self.ui.game_canvas.delete("grid")

        if not self._grid_enabled:
            return

        scale = self.mesh_graph.half_scale_x * 0.01

        def draw_line(x0, y0, x1, y1):
            x0_ = self.mesh_graph.mesh_to_screen_x(x0, 0)
            y0_ = self.mesh_graph.mesh_to_screen_y(y0, 0)
            x1_ = self.mesh_graph.mesh_to_screen_x(x1, 0)
            y1_ = self.mesh_graph.mesh_to_screen_y(y1, 0)
            self.ui.game_canvas.create_line(x0_, y0_, x1_, y1_, width=0.01, fill="#884488", tag="grid")

        for x in range(self.mesh_graph.mesh_width + 1):
            draw_line(x - 0.5, -0.5, x - 0.5, self.mesh_graph.mesh_height - 0.5)

        for y in range(self.mesh_graph.mesh_height + 1):
            draw_line(-0.5, y - 0.5, self.mesh_graph.mesh_width - 0.5, y - 0.5)

    def draw_line_of_sight(self, game_state):
        self.ui.game_canvas.delete("line_of_sight")
        if not self._grid_enabled:
            return

        scale = self.mesh_graph.half_scale_x * 0.1

        def draw_box(pos):
            ul = self.mesh_graph.mesh_to_screen(pos, (-1, -1))
            ur = self.mesh_graph.mesh_to_screen(pos, (1, -1))
            ll = self.mesh_graph.mesh_to_screen(pos, (-1, 1))
            lr = self.mesh_graph.mesh_to_screen(pos, (1, 1))

            self.ui.game_canvas.create_rectangle(*ul, *lr, width=2, outline='#111', tag=("line_of_sight",))

        bot = game_state['turn']
        if bot is None:
            # game has not started yet
            return

        try:
            old_pos = tuple(game_state['requested_moves'][bot]['previous_position'])
        except TypeError:
            old_pos = game_state['bots'][bot]
        draw_box(old_pos)

        sight_distance = game_state["sight_distance"]
        # starting from old_pos, iterate over all positions that are up to sight_distance
        # steps away and put a border around the fields.
        border_cells_relative = set(
            (dx, dy)
            for dx in range(- sight_distance, sight_distance + 1)
            for dy in range(- sight_distance, sight_distance + 1)
            if abs(dx) + abs(dy) == sight_distance
        )

        def in_maze(x, y):
            return 0 <= x < game_state['shape'][0] and  0 <= y < game_state['shape'][1]

        def on_edge(x, y):
            return x == 0 or x == game_state['shape'][0] - 1 or y == 0 or y == game_state['shape'][1] - 1


        def draw_line(pos, color, loc):
            x0_ = self.mesh_graph.mesh_to_screen_x(pos[0], loc[0])
            y0_ = self.mesh_graph.mesh_to_screen_y(pos[1], loc[1])
            x1_ = self.mesh_graph.mesh_to_screen_x(pos[0], loc[2])
            y1_ = self.mesh_graph.mesh_to_screen_y(pos[1], loc[3])
            self.ui.game_canvas.create_line(x0_, y0_, x1_, y1_, width=2, fill=color, tag=("line_of_sight"))

        team_col = STRONG_BLUE if bot % 2 == 0 else STRONG_RED


        def draw_box(pos, fill):
            ul = self.mesh_graph.mesh_to_screen(pos, (-1, -1))
            ur = self.mesh_graph.mesh_to_screen(pos, (1, -1))
            ll = self.mesh_graph.mesh_to_screen(pos, (-1, 1))
            lr = self.mesh_graph.mesh_to_screen(pos, (1, 1))

            self.ui.game_canvas.create_rectangle(*ul, *lr, width=0, fill=fill, tag=("line_of_sight", "area_of_sight"))

        for dx in range(- sight_distance, sight_distance + 1):
            for dy in range(- sight_distance, sight_distance + 1):
                if abs(dx) + abs(dy) > sight_distance:
                    continue

                pos = (old_pos[0] + dx, old_pos[1] + dy)
                if not in_maze(pos[0], pos[1]):
                    continue

                draw_box(pos, fill=LIGHT_BLUE if bot % 2 == 0 else LIGHT_RED)

                # add edge around cells at the line of sight max
                if (dx, dy) in border_cells_relative:
                    if dx >= 0:
                        draw_line(pos, loc=(1, 1, 1, -1), color=team_col)
                    if dx <= 0:
                        draw_line(pos, loc=(-1, 1, -1, -1), color=team_col)
                    if dy >= 0:
                        draw_line(pos, loc=(1, 1, -1, 1), color=team_col)
                    if dy <= 0:
                        draw_line(pos, loc=(1, -1, -1, -1), color=team_col)

                # add edge around cells at the edge of the maze
                if on_edge(pos[0], pos[1]):
                    if pos[0] == game_state['shape'][0] - 1:
                        draw_line(pos, loc=(1, 1, 1, -1), color=team_col)
                    if pos[0] == 0:
                        draw_line(pos, loc=(-1, 1, -1, -1), color=team_col)
                    if pos[1] == game_state['shape'][1] - 1:
                        draw_line(pos, loc=(1, 1, -1, 1), color=team_col)
                    if pos[1] == 0:
                        draw_line(pos, loc=(1, -1, -1, -1), color=team_col)

        self.ui.game_canvas.tag_lower("area_of_sight")
        self.ui.game_canvas.tag_raise("wall")


    def toggle_grid(self):
        self._grid_enabled = not self._grid_enabled
        self.size_changed = True
        self._check_grid_toggle_state()
        self.update()

    def _check_grid_toggle_state(self):
        if self._grid_enabled:
            self.ui.button_game_toggle_grid.config(text="debug")
        else:
            self.ui.button_game_toggle_grid.config(text="debug")

    def on_click(self, event):
        raw_x, raw_y = event.x, event.y
        selected = self.mesh_graph.screen_to_mesh_coord(event.x, event.y)
        if self.selected == selected:
            self.selected = None
        else:
            self.selected = selected
        self.update()

    def draw_background(self):
        """ Draws a line between blue and red team.
        """
        if not self.size_changed:
            return
        self.ui.game_canvas.delete("background")

        center = self.mesh_graph.screen_width // 2
        cols = (BLUE, RED, GREY)

        scale = self.mesh_graph.half_scale_x * 0.2

        for color, x_orig in zip(cols, (center - 3, center + 3, center)):
            y_top = self.mesh_graph.mesh_to_screen_y(0, 0)
            y_bottom = self.mesh_graph.mesh_to_screen_y(self.mesh_graph.mesh_height - 1, 0)
            self.ui.game_canvas.create_line(x_orig, y_top, x_orig, y_bottom, width=scale, fill=color, tag="background")

    def draw_title(self, game_state):
        self.ui.header_canvas.delete("title")

        center = self.ui.header_canvas.winfo_width() // 2

        try:
            team_time = game_state["team_time"]
        except (KeyError, TypeError):
            team_time = [0, 0]

        left_team = "%s %d " % (game_state["team_names"][0], game_state["score"][0])
        right_team = " %d %s" % (game_state["score"][1], game_state["team_names"][1])
        font_size = guess_size(left_team + ' : ' + right_team,
                               self.ui.header_canvas.winfo_width(),
                               30,
                               rel_size = 1)

        def status(team_idx):
            try:
                # sum the deaths of both bots in this team
                deaths = game_state['deaths'][team_idx] + game_state['deaths'][team_idx+2]
                kills = game_state['kills'][team_idx] + game_state['kills'][team_idx+2]
                ret = "Errors: %d, Kills: %d, Deaths: %d, Time: %.2f" % (game_state["num_errors"][team_idx], kills, deaths, game_state["team_time"][team_idx])
                return ret
            except TypeError:
                return ""

        left_status = status(0)
        right_status = status(1)
        status_font_size = max(font_size - 5, 3)

        top = 15
        spacer = 3

        middle_colon = self.ui.header_canvas.create_text(center, top, text=":", font=(None, font_size), tag="title", anchor=tkinter.CENTER)
        middle_colon_bottom = self.ui.header_canvas.bbox(middle_colon)[3]
        spacer = (self.ui.header_canvas.bbox(middle_colon)[3] - self.ui.header_canvas.bbox(middle_colon)[1]) / 2

        self.ui.header_canvas.create_text(center, top, text=left_team, font=(None, font_size), fill=BLUE, tag="title", anchor=tkinter.E)
        self.ui.header_canvas.create_text(center+2, top, text=right_team, font=(None, font_size), fill=RED, tag="title", anchor=tkinter.W)

        bottom_text = self.ui.header_canvas.create_text(0 + 5, 20 + font_size, text=" " + left_status, font=(None, status_font_size), tag="title", anchor=tkinter.W)
        self.ui.header_canvas.create_text(self.ui.header_canvas.winfo_width() - 5, 20 + font_size, text=right_status + " ", font=(None, status_font_size), tag="title", anchor=tkinter.E)

    def draw_status_info(self, game_state):
        round = "–" if game_state["round"] is None else game_state["round"]
        max_rounds = "–" if game_state["max_rounds"] is None else game_state["max_rounds"]
        turn = "–" if game_state["turn"] is None else game_state["turn"]
        layout_name = "–" if game_state["layout_name"] is None else game_state["layout_name"]

        round_info = f"Round {round:>3}/{max_rounds}"
        self.ui.status_round_info.config(text=round_info)

        if self._fps is not None:
            fps_info = "%.f fps" % self._fps
        else:
            fps_info = "– fps"
        self.ui.status_fps_info.config(text=fps_info)

        bot_colors = [BLUE, RED, BLUE, RED]
        for idx, circle in enumerate(self.ui.bot_traffic_lights_c):
            if turn == idx:
                self.ui.bot_traffic_lights_canvas.itemconfig(circle, fill=bot_colors[idx])
            else:
                self.ui.bot_traffic_lights_canvas.itemconfig(circle, fill="#bbb")

        self.ui.status_layout_info.config(text=layout_name)

    def draw_selected(self, game_state):
        self.ui.game_canvas.delete("selected")
        if self.selected:
            def field_status(pos):
                has_food = pos in game_state['food']
                is_wall = pos in game_state['walls']
                bots = [idx for idx, bot in enumerate(game_state['bots']) if bot==pos]
                if pos[0] <= (game_state['shape'][0] // 2):
                    zone = "blue"
                else:
                    zone = "red"

                if is_wall:
                    contents = ["wall"]
                elif has_food:
                    contents = ["food"]
                else:
                    contents = []

                if bots:
                    bot_map = {0:'blue 0', 1:'red 0', 2:'blue 1', 3:'red 1'}
                    contents += ["bots(" \
                                 + ", ".join(bot_map[bot] for bot in bots) \
                                 + ")"]

                contents = " ".join(contents)
                if not contents:
                    contents = "empty"

                return f"{pos} in {zone} zone: {contents}"

            self.ui.status_selected.config(text=field_status(self.selected))

            ul = self.mesh_graph.mesh_to_screen(self.selected, (-1, -1))
            ur = self.mesh_graph.mesh_to_screen(self.selected, (1, -1))
            ll = self.mesh_graph.mesh_to_screen(self.selected, (-1, 1))
            lr = self.mesh_graph.mesh_to_screen(self.selected, (1, 1))

            self.ui.game_canvas.create_rectangle(*ul, *lr, fill='#dddddd', tag=("selected",))
            self.ui.game_canvas.tag_lower("selected")
        else:
            self.ui.status_selected.config(text="nothing selected")


    def draw_end_of_game(self, display_string):
        """ Draw an end of game string. """
        self.ui.game_canvas.delete("gameover")

        if display_string is None:
            return

        center = (self.mesh_graph.screen_width // 2,
                  self.mesh_graph.screen_height //2)

        font_size = guess_size(display_string,
                               self.mesh_graph.screen_width,
                               self.mesh_graph.screen_height,
                               rel_size = +1)

        for i in [-2, -1, 0, 1, 2]:
            for j in [-2, -1, 0, 1, 2]:
                self.ui.game_canvas.create_text(center[0] - i, center[1] - j,
                        text=display_string,
                        font=(None, font_size, "bold"),
                        fill="#ED1B22", tag="gameover",
                        justify=tkinter.CENTER, anchor=tkinter.CENTER)

        self.ui.game_canvas.create_text(center[0] , center[1] ,
                text=display_string,
                font=(None, font_size, "bold"),
                fill="#FFC903", tag="gameover",
                justify=tkinter.CENTER, anchor=tkinter.CENTER)


    def draw_game_over(self, win_name):
        """ Draw the game over string. """
        # shorten the winning name
        plural = '' if win_name.endswith('s') else 's'
        if len(win_name) > 25:
            win_name = win_name[:22] + '...'
        self.draw_end_of_game("GAME OVER\n%s win%s!" % (win_name, plural))

    def draw_game_draw(self):
        """ Draw the game draw string. """
        self.draw_end_of_game("GAME OVER\nDRAW!")

    def clear(self):
        self.ui.game_canvas.delete(tkinter.ALL)

    def draw_food(self, game_state):
        if not self.size_changed:
            return
        self.ui.game_canvas.delete("food")
        self.food_items = {}
        for position in game_state['food']:
            model_x, model_y = position
            food_item = Food(self.mesh_graph, position=(model_x, model_y))
            food_item.draw(self.ui.game_canvas)
            self.food_items[position] = food_item

    def draw_maze(self, game_state):
        if not self.size_changed:
            return
        self.ui.game_canvas.delete("wall")
        # we keep all wall items stored in a list
        # some versions of Python seem to forget about drawing
        # them otherwise
        self.wall_items = []
        num = 0
        for wall in game_state['walls']:
            model_x, model_y = wall
            wall_neighbors = [(dx, dy)
                              for dx in [-1, 0, 1]
                              for dy in [-1, 0, 1]
                              if (model_x + dx, model_y + dy) in game_state['walls']]
            wall_item = Wall(self.mesh_graph, wall_neighbors=wall_neighbors, position=(model_x, model_y))
            wall_item.draw(self.ui.game_canvas)
            self.wall_items.append(wall_item)
            num += 1

    def init_bot_sprites(self, bot_positions):
        for sprite in self.bot_sprites.values():
            sprite.delete(self.ui.game_canvas)
        self.bot_sprites = {
            idx: BotSprite(self.mesh_graph, team=idx % 2, bot_id=idx, position=bot)
            for idx, bot in enumerate(bot_positions)
        }
        for sprite in self.shadow_sprites.values():
            sprite.delete(self.ui.game_canvas)
        self.shadow_sprites = {
            idx: BotSprite(self.mesh_graph, team=idx % 2, bot_id=idx, position=None, shadow=True)
            for idx, bot in enumerate(bot_positions)
        }

    def draw_moves(self, game_state):
        if game_state['turn'] is None:
            return

        self.ui.game_canvas.delete("arrow")
        # we keep all arrow items stored in a list
        # some versions of Python seem to forget about drawing
        # them otherwise
        self.arrow_items = []

        if not self._grid_enabled:
            return

        bot = game_state['turn']
        try:
            old_pos = tuple(game_state['requested_moves'][bot]['previous_position'])
        except TypeError:
            old_pos = None
        try:
            req_pos = tuple(game_state['requested_moves'][bot]['requested_position'])
        except TypeError:
            req_pos = None
        arrow_item = Arrow(self.mesh_graph,
                           position=old_pos,
                           req_pos=game_state['bots'][bot],
                           success=game_state['requested_moves'][bot]['success'])
        arrow_item.draw(self.ui.game_canvas)
        self.arrow_items.append(arrow_item)

    def draw_bots(self, game_state):
        if game_state:
            for bot_id, was_killed in enumerate(game_state["bot_was_killed"]):
                if was_killed:
                    self.bot_sprites[bot_id].position = None

        for bot_id, bot_sprite in self.bot_sprites.items():
            say = game_state and game_state["say"][bot_id]
            bot_sprite.move_to(game_state["bots"][bot_sprite.bot_id],
                               self.ui.game_canvas,
                               game_state,
                               force=self.size_changed,
                               say=say,
                               show_id=self._grid_enabled)

    def draw_shadow_bots(self, game_state):
        # Draw the shadowbots when debug mode (grid) is enabled
        # Otherwise make sure that they are deleted

        if game_state['turn'] is None:
            # We cannot show shadow bots before the first turn has been played,
            # as we would only see the bots from the set_initial phase, and
            # only the blue bots (those that were shown to the second, red, player).
            # Given that this information is not available to the client API,
            # we must hide the shadow bots here.
            # TODO: This should be fixed inside game.py
            return

        for bot_id, bot_sprite in self.shadow_sprites.items():
            if self._grid_enabled:
                shadow_bots = game_state.get('noisy_positions')
            else:
                shadow_bots = None

            if shadow_bots is None or shadow_bots[bot_id] is None:
                bot_sprite.delete(self.ui.game_canvas)
            else:
                bot_sprite.move_to(shadow_bots[bot_id],
                                    self.ui.game_canvas,
                                    game_state,
                                    force=self.size_changed,
                                    show_id=self._grid_enabled)

    def toggle_running(self):
        # We change from running to stopping or the other way round
        # Clean up the times for fps calculation as they will be wrong
        self._fps = None
        self._times = []

        self.running = not self.running
        if self.running:
            self.request_step()

    def request_initial(self):
        if self.controller_socket:
            _logger.debug('---> set_initial')
            self.controller_socket.send_json({"__action__": "set_initial"})

    def request_step(self):
        if not self.controller_socket:
            return

        if self._game_state['gameover']:
            return

        if self._stop_after is not None:
            next_step = next_round_turn(self._game_state)
            if (next_step['round'] < self._stop_after):
                _logger.debug('---> play_step')
                self.controller_socket.send_json({"__action__": "play_step"})
            else:
                self._stop_after = None
                self.running = False
                self._delay = self._stop_after_delay
        else:
            _logger.debug('---> play_step')
            self.controller_socket.send_json({"__action__": "play_step"})

    def request_round(self):
        if not self.controller_socket:
            return

        if self._game_state['gameover']:
            return

        if self._game_state['round'] is not None:
            next_step = next_round_turn(self._game_state)
            self._stop_after = next_step['round'] + 1
        else:
            self._stop_after = 1
            self._delay = self._min_delay
        self.request_step()

    def observe(self, game_state):
        step = (game_state['round'], game_state['turn'])
        if step in self._observed_steps:
            skip_request = True
        else:
            skip_request = False
            self._observed_steps.add(step)
        # ensure walls, foods and bots positions are list of tuples
        game_state['walls'] = _ensure_list_tuples(game_state['walls'])
        game_state['food'] = _ensure_list_tuples(game_state['food'])
        game_state['bots'] = _ensure_list_tuples(game_state['bots'])
        game_state['shape'] = tuple(game_state['shape'])
        self.update(game_state)
        if self._stop_after is not None:
            if self._stop_after == 0:
                self._stop_after = None
                self.running = False
                self._delay = self._stop_after_delay
            else:
                if skip_request:
                    _logger.debug("Skipping next request.")
                else:
                    self.master.after(self._delay, self.request_step)
        elif self.running:
            if skip_request:
                _logger.debug("Skipping next request.")
            else:
                self.master.after(self._delay, self.request_step)


    def on_quit(self):
        """ override for things which must be done when we exit.
        """
        self.running = False
        if self.controller_socket:
            _logger.debug('---> exit')
            self.controller_socket.send_json({"__action__": "exit"})
        else:
            # force closing the window (though this might not work)
            wm_delete_window_handler()

    def quit(self):
        self.on_quit()
        self.master.quit()

    def delay_inc(self):
        self._delay += 5
        self._check_speed_button_state()

    def delay_dec(self):
        # Tk may break if self._delay is lower than zero.
        # (For some systems a value < 1 is already too fast.)
        self._delay = max(self._delay - 5, self._min_delay)
        self._check_speed_button_state()

    def _check_speed_button_state(self):
        try:
            # self.ui.button_game_speed_faster
            # may not be available yet (or may be None).
            # If this is the case, we’ll do nothing at all.
            if self._delay <= self._min_delay:
                self.ui.button_game_speed_faster.config(state=tkinter.DISABLED)
            else:
                self.ui.button_game_speed_faster.config(state=tkinter.NORMAL)
        except AttributeError:
            pass
