import json
import logging
import time

import zmq

import tkinter
import tkinter.font

from ..datamodel import CTFUniverse
from ..libpelita import firstNN
from .tk_sprites import BotSprite, Food, Wall, col
from .tk_utils import wm_delete_window_handler
from .tk_sprites import BotSprite, Food, Wall, RED, BLUE, YELLOW, GREY, BROWN 

_logger = logging.getLogger("pelita.tk")



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
                 geometry=None, delay=1):
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

        self._universe = None
        self._game_state = None

        self.ui = UI()

        self.ui.header_canvas = tkinter.Canvas(master, height=50)
        self.ui.header_canvas.config(background="white")
        
        self.ui.sub_header = tkinter.Frame(master, height=25)
        self.ui.sub_header.config(background="white")

        self.ui.status_canvas = tkinter.Frame(master, height=25)
        self.ui.status_canvas.config(background="white")

        self.ui.game_canvas = tkinter.Canvas(master)
        self.ui.game_canvas.config(background="white")
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
        self._check_speed_button_state()

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


    def init_mesh(self, universe):
        width = universe.maze.width
        height = universe.maze.height

        if self.geometry is None:
            screensize = (
                max(250, app.winfo_screenwidth() - 100),
                max(250, app.winfo_screenheight() - 100)
                )
        else:
            screensize = self.geometry
        scale_x = screensize[0] / width
        scale_y = screensize[1] / height
        scale = int(min(scale_x, scale_y, 50))

        self.mesh_graph = MeshGraph(width, height, scale * width, scale * height)
        self.init_bot_sprites(universe)

    def update(self, universe=None, game_state=None):
        # Update the times for the fps calculation (if we are running)
        # Our fps is only relevant for how often the bots update our viewer.
        # When the viewer updates itself, we do not count it.
        if self.running and universe and game_state:
            self._times.append(time.monotonic())
            if len(self._times) > 3:
                # take the mean of the last two time differences
                # this could also be improved by taking up to four if available
                self._fps = 2 / ((self._times[-1] - self._times[-2]) + (self._times[-2] - self._times[-3]))
            else:
                self._fps = None
            if len(self._times) > 100:
                # Garbage collect old times
                self._times = self._times[-3:]

        if universe is not None:
            self._universe = universe
        if game_state is not None:
            self._game_state = game_state
        universe = self._universe
        game_state = self._game_state

        if not universe:
            return

        if game_state['game_uuid'] != self.game_uuid:
            self.game_uuid = game_state['game_uuid']
            self.init_mesh(universe)

        if ((self.mesh_graph.screen_width, self.mesh_graph.screen_height)
            != (self.ui.game_canvas.winfo_width(), self.ui.game_canvas.winfo_height())):
            self.size_changed = True

        self.mesh_graph.screen_width = self.ui.game_canvas.winfo_width()
        self.mesh_graph.screen_height = self.ui.game_canvas.winfo_height()

        if self.mesh_graph.screen_width < 600:
            self._default_font.configure(size=8)
        else:
            if self._default_font.cget('size') != self._default_font_size:
                self._default_font.configure(size=self._default_font_size)

        self.draw_universe(universe, game_state)

        for food_eaten in game_state["food_eaten"]:
            food_tag = Food.food_pos_tag(tuple(food_eaten["food_pos"]))
            self.ui.game_canvas.delete(food_tag)

        winning_team_idx = game_state.get("team_wins")
        if winning_team_idx is not None:
            team_name = game_state["team_name"][winning_team_idx]
            self.draw_game_over(team_name)
        elif game_state.get("game_draw"):
            self.draw_game_draw()
        else:
            self.draw_end_of_game(None)

        self.size_changed = False

    def draw_universe(self, universe, game_state):
        self.mesh_graph.num_x = universe.maze.width
        self.mesh_graph.num_y = universe.maze.height

        self.draw_grid(universe)
        self.draw_selected(universe, game_state)
        self.draw_background(universe)
        self.draw_maze(universe)
        self.draw_food(universe)

        self.draw_title(universe, game_state)
        self.draw_bots(universe, game_state)

        self.draw_status_info(universe, game_state)

    def draw_grid(self, universe):
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

        for x in range(self.mesh_graph.mesh_width):
            draw_line(x - 0.5, 0, x - 0.5, self.mesh_graph.mesh_height - 1)

        for y in range(self.mesh_graph.mesh_height):
            draw_line(0, y - 0.5, self.mesh_graph.mesh_width - 1, y - 0.5)

    def toggle_grid(self):
        self._grid_enabled = not self._grid_enabled
        self.size_changed = True
        self._check_grid_toggle_state()
        self.update()

    def _check_grid_toggle_state(self):
        if self._grid_enabled:
            self.ui.button_game_toggle_grid.config(text="hide grid")
        else:
            self.ui.button_game_toggle_grid.config(text="show grid")

    def on_click(self, event):
        raw_x, raw_y = event.x, event.y
        x = int(raw_x / self.mesh_graph.screen_width * self.mesh_graph.mesh_width)
        y = int(raw_y / self.mesh_graph.screen_height * self.mesh_graph.mesh_height)
        if self.selected == (x, y):
            self.selected = None
        else:
            self.selected = (x, y)
        self.update()

    def draw_background(self, universe):
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

    def draw_title(self, universe, game_state):
        self.ui.header_canvas.delete("title")

        center = self.ui.header_canvas.winfo_width() // 2

        try:
            team_time = game_state["team_time"]
        except (KeyError, TypeError):
            team_time = [0, 0]

        left_team = "%s %d " % (game_state["team_name"][0], universe.teams[0].score)
        right_team = " %d %s" % (universe.teams[1].score, game_state["team_name"][1])
        font_size = guess_size(left_team + ' : ' + right_team,
                               self.ui.header_canvas.winfo_width(),
                               30,
                               rel_size = 1)

        def status(team_idx):
            try:
                ret = "Timeouts: %d, Killed: %d, Time: %.2f" % (game_state["timeout_teams"][team_idx], game_state["times_killed"][team_idx], game_state["team_time"][team_idx])
                disqualified = game_state["teams_disqualified"][team_idx]
                if disqualified is not None:
                    ret += ", Disqualified: %s" % disqualified
                return ret
            except TypeError:
                return ""

        left_status = status(0)
        right_status = status(1)
        status_font_size = max(font_size - 3, 3)

        top = 15
        spacer = 3

        middle_colon = self.ui.header_canvas.create_text(center, top, text=":", font=(None, font_size), tag="title", anchor=tkinter.CENTER)
        middle_colon_bottom = self.ui.header_canvas.bbox(middle_colon)[3]
        spacer = (self.ui.header_canvas.bbox(middle_colon)[3] - self.ui.header_canvas.bbox(middle_colon)[1]) / 2

        self.ui.header_canvas.create_text(center, top, text=left_team, font=(None, font_size), fill=BLUE, tag="title", anchor=tkinter.E)
        self.ui.header_canvas.create_text(center+2, top, text=right_team, font=(None, font_size), fill=RED, tag="title", anchor=tkinter.W)

        bottom_text = self.ui.header_canvas.create_text(0 + 5, 15 + font_size, text=" " + left_status, font=(None, status_font_size), tag="title", anchor=tkinter.W)
        self.ui.header_canvas.create_text(self.ui.header_canvas.winfo_width() - 5, 15 + font_size, text=right_status + " ", font=(None, status_font_size), tag="title", anchor=tkinter.E)

        height = self.ui.header_canvas.bbox(bottom_text)[3]
        self.ui.header_canvas.configure(height=height)

    def draw_status_info(self, universe, game_state):
        round = firstNN(game_state.get("round_index"), "–")
        max_rounds = firstNN(game_state.get("game_time"), "–")
        turn = firstNN(game_state.get("bot_id"), "–")
        layout_name = firstNN(game_state.get("layout_name"), "–")

        roundturn = "Bot %s, Round % 3s/%s" % (turn, round, max_rounds)

        if self._fps is not None:
            fps_info = "%.f fps" % self._fps
        else:
            fps_info = "– fps"
        self.ui.status_fps_info.config(text=fps_info, )

        self.ui.status_round_info.config(text=roundturn)
        self.ui.status_layout_info.config(text=layout_name)

    def draw_selected(self, universe, game_state):
        self.ui.game_canvas.delete("selected")
        if self.selected:
            def field_status(pos):
                has_food = pos in universe.food
                is_wall = universe.maze[pos]
                bots = [str(bot.index) for bot in universe.bots if bot.current_pos == pos]
                if pos[0] < universe.maze.width // 2:
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
                    contents += ["bots(" + ",".join(bots) + ")"]

                contents = " ".join(contents)
                if not contents:
                    contents = "empty"

                return "[{x}, {y}] in {color} zone: {contents}".format(
                    x=pos[0], y=pos[1], color=zone, contents=contents)

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

    def draw_food(self, universe):
        if not self.size_changed:
            return
        self.ui.game_canvas.delete("food")
        for position in universe.food_list:
            model_x, model_y = position
            food_item = Food(self.mesh_graph, position=(model_x, model_y))
            food_item.draw(self.ui.game_canvas)

    def draw_maze(self, universe):
        if not self.size_changed:
            return
        self.ui.game_canvas.delete("wall")
        num = 0
        for position, wall in universe.maze.items():
            model_x, model_y = position
            if wall:
                wall_neighbors = [(dx, dy)
                                  for dx in [-1, 0, 1]
                                  for dy in [-1, 0, 1]
                                  if universe.maze.get((model_x + dx, model_y + dy), None)]
                wall_item = Wall(self.mesh_graph, wall_neighbors=wall_neighbors, position=(model_x, model_y))
                wall_item.draw(self.ui.game_canvas)
                num += 1

    def init_bot_sprites(self, universe):
        for sprite in self.bot_sprites.values():
            sprite.delete(self.ui.game_canvas)
        self.bot_sprites = {
            bot.index: BotSprite(self.mesh_graph, team=bot.team_index, bot_id=bot.index, position=bot.current_pos)
            for bot in universe.bots
        }

    def draw_bots(self, universe, game_state):
        if game_state:
            for bot in game_state["bot_destroyed"]:
                self.bot_sprites[bot["bot_id"]].position = None
        for bot_id, bot_sprite in self.bot_sprites.items():
            say = game_state and game_state["bot_talk"][bot_id]
            bot_sprite.move_to(universe.bots[bot_sprite.bot_id].current_pos,
                               self.ui.game_canvas,
                               universe,
                               force=self.size_changed,
                               say=say,
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
            self.controller_socket.send_json({"__action__": "set_initial"})

    def request_step(self):
        if self.controller_socket:
            self.controller_socket.send_json({"__action__": "play_step"})

    def request_round(self):
        if self.controller_socket:
            self.controller_socket.send_json({"__action__": "play_round"})

    def observe(self, data):
        universe = data["universe"]
        universe = CTFUniverse._from_json_dict(universe)
        game_state = data["game_state"]

        self.update(universe, game_state)
        if self.running:
            self.master.after(self._delay, self.request_step)

    def on_quit(self):
        """ override for things which must be done when we exit.
        """
        self.running = False
        if self.controller_socket:
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
