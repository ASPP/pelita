import json
import logging
import time

import zmq

import tkinter
import tkinter.font

from ..datamodel import CTFUniverse
from ..utils.signal_handlers import wm_delete_window_handler
from .tk_sprites import BotSprite, Food, Wall, col

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



class UiCanvas:
    def __init__(self, master, geometry=None):
        self.game_finish_overlay = lambda: None
        self.game_status_info = lambda: None

        self.mesh_graph = None
        self.geometry = geometry

        self.size_changed = True

        self.master = master
        self.canvas = None

        self.current_universe = None

        self._grid_enabled = False

        self.timestamp = time.time()
        self.fps = 0

    def init_canvas(self):
        self.score = tkinter.Canvas(self.master.frame, width=self.mesh_graph.screen_width, height=40)
        self.score.config(background="white")
        self.score.pack(side=tkinter.TOP, fill=tkinter.X)

        self.status = tkinter.Canvas(self.master.frame, width=self.mesh_graph.screen_width, height=25)
        self.status.config(background="white")
        self.status.pack(side=tkinter.BOTTOM, fill=tkinter.X)

        game_control_frame = tkinter.Frame(self.status, background="white")
        game_control_frame.grid(row=0, sticky="W")
        game_speed_frame = tkinter.Frame(self.status, background="white")
        game_speed_frame.grid(row=1, sticky="W")

        self.status_round_info = tkinter.Label(self.status, text="", background="white")
        self.status_round_info.grid(row=0, column=2, sticky="E")

        self.status_layout_info = tkinter.Label(self.status, text="", background="white")
        self.status_layout_info.grid(row=1, column=2, sticky="E")

        self.button_game_speed_slower = tkinter.Button(game_speed_frame,
            foreground="black",
            background="white",
            justify=tkinter.CENTER,
            text="slower",
            command=self.master.delay_inc)
        self.button_game_speed_slower.pack(side=tkinter.LEFT)

        self.button_game_speed_faster = tkinter.Button(game_speed_frame,
            foreground="black",
            background="white",
            justify=tkinter.CENTER,
            text="faster",
            command=self.master.delay_dec)
        self.button_game_speed_faster.pack(side=tkinter.LEFT)

        self.master._check_speed_button_state()

        self.button_game_toggle_grid = tkinter.Button(game_speed_frame,
            foreground="black",
            background="white",
            justify=tkinter.CENTER,
            command=self.toggle_grid)
        self.button_game_toggle_grid.pack(side=tkinter.LEFT)

        self._check_grid_toggle_state()

        self.status_fps_info = tkinter.Label(game_speed_frame, text="", fg="#acacac", background="white", anchor="s")
        self.status_fps_info.pack(side=tkinter.LEFT)

        tkinter.Button(game_control_frame,
                       foreground="black",
                       background="white",
                       justify=tkinter.CENTER,
                       text="PLAY/PAUSE",
                       command=self.master.toggle_running).pack(side=tkinter.LEFT)

        tkinter.Button(game_control_frame,
                       foreground="black",
                       background="white",
                       justify=tkinter.CENTER,
                       text="STEP",
                       command=self.master.request_step).pack(side=tkinter.LEFT)

        tkinter.Button(game_control_frame,
                       foreground="black",
                       background="white",
                       justify=tkinter.CENTER,
                       text="ROUND",
                       command=self.master.request_round).pack(side=tkinter.LEFT)

        tkinter.Button(self.status,
                       foreground="black",
                       background="white",
                       justify=tkinter.CENTER,
                       text="QUIT",
                       command=self.master.quit).grid(row=0, column=1, rowspan=2, sticky="WE")


        self.status.grid_columnconfigure(0, weight=1)
        self.status.grid_columnconfigure(1, weight=1)
        self.status.grid_columnconfigure(2, weight=1)

        self.canvas = tkinter.Canvas(self.master.frame,
                                     width=self.mesh_graph.screen_width,
                                     height=self.mesh_graph.screen_height)
        self.canvas.config(background="white")
        self.canvas.pack(fill=tkinter.BOTH, expand=tkinter.YES)
        self.canvas.bind('<Configure>', self.resize)

    def update(self, universe, game_state):
        # This method is called every now and then. Either when new information
        # about universe or game_state have arrived or when a resize has occurred.
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

        if game_state:
            round = game_state.get("round_index")
            turn = game_state.get("bot_id")
        else:
            round = None
            turn = None

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
            self.game_status_info = lambda: self.draw_status_info(turn, round, game_state.get("layout_name", ""))
        self.game_status_info()

        self.draw_universe(self.current_universe, game_state)

        if game_state:
            for food_eaten in game_state["food_eaten"]:
                food_tag = Food.food_pos_tag(tuple(food_eaten["food_pos"]))
                self.canvas.delete(food_tag)

            winning_team_idx = game_state.get("team_wins")
            if winning_team_idx is not None:
                team_name = game_state["team_name"][winning_team_idx]
                self.game_finish_overlay = lambda: self.draw_game_over(team_name)

            if game_state.get("game_draw"):
                self.game_finish_overlay = lambda: self.draw_game_draw()

        self.game_finish_overlay()


    def draw_universe(self, universe, game_state):
        self.mesh_graph.num_x = universe.maze.width
        self.mesh_graph.num_y = universe.maze.height

        self.draw_grid(universe)
        self.draw_background(universe)
        self.draw_maze(universe)
        self.draw_food(universe)

        self.draw_title(universe, game_state)
        self.draw_bots(universe, game_state)

        self.size_changed = False

    def draw_grid(self, universe):
        """ Draws a light grid on the background.
        """
        if not self.size_changed:
            return
        self.canvas.delete("grid")

        if not self._grid_enabled:
            return

        scale = self.mesh_graph.half_scale_x * 0.01

        def draw_line(x0, y0, x1, y1):
            x0_ = self.mesh_graph.mesh_to_screen_x(x0, 0)
            y0_ = self.mesh_graph.mesh_to_screen_y(y0, 0)
            x1_ = self.mesh_graph.mesh_to_screen_x(x1, 0)
            y1_ = self.mesh_graph.mesh_to_screen_y(y1, 0)
            self.canvas.create_line(x0_, y0_, x1_, y1_, width=0.01, fill="#884488", tag="grid")

        for x in range(self.mesh_graph.mesh_width):
            draw_line(x - 0.5, 0, x - 0.5, self.mesh_graph.mesh_height - 1)

        for y in range(self.mesh_graph.mesh_height):
            draw_line(0, y - 0.5, self.mesh_graph.mesh_width - 1, y - 0.5)

    def toggle_grid(self):
        self._grid_enabled = not self._grid_enabled
        self.size_changed = True
        self._check_grid_toggle_state()

    def _check_grid_toggle_state(self):
        if self._grid_enabled:
            self.button_game_toggle_grid.config(text="hide grid")
        else:
            self.button_game_toggle_grid.config(text="show grid")

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
            y_top = self.mesh_graph.mesh_to_screen_y(0, 0)
            y_bottom = self.mesh_graph.mesh_to_screen_y(self.mesh_graph.mesh_height - 1, 0)
            self.canvas.create_line(x_orig, y_top, x_orig, y_bottom, width=scale, fill=color, tag="background")

    def draw_title(self, universe, game_state):
        self.score.delete("title")
        if not game_state:
            return

        center = self.mesh_graph.screen_width // 2

        try:
            team_time = game_state["team_time"]
        except (KeyError, TypeError):
            team_time = [0, 0]

        left_team = "(%.2f) %s %d " % (team_time[0], game_state["team_name"][0], universe.teams[0].score)
        right_team = " %d %s (%.2f)" % (universe.teams[1].score, game_state["team_name"][1], team_time[1])
        font_size = guess_size(left_team+':'+right_team,
                               self.mesh_graph.screen_width,
                               30,
                               rel_size = +1)

        def status(team_idx):
            try:
                return "Timeouts: %i, Killed: %i" % (game_state["timeout_teams"][team_idx], game_state["times_killed"][team_idx])
            except TypeError:
                return ""

        left_status = status(0)
        right_status = status(1)
        status_font_size = max(font_size - 3, 3)

        self.score.create_text(center, 15, text=left_team, font=(None, font_size), fill=col(94, 158, 217), tag="title", anchor=tkinter.E)

        self.score.create_text(center, 15, text=":", font=(None, font_size), tag="title", anchor=tkinter.CENTER)

        self.score.create_text(center+2, 15, text=right_team, font=(None, font_size), fill=col(235, 90, 90), tag="title", anchor=tkinter.W)

        self.score.create_text(center, 35, text="|", font=(None, font_size), tag="title", anchor=tkinter.CENTER)
        self.score.create_text(center, 35, text=left_status + " ", font=(None, status_font_size), tag="title", anchor=tkinter.E)
        self.score.create_text(center+1, 35, text=" " + right_status, font=(None, status_font_size), tag="title", anchor=tkinter.W)

    FPS_MULT = 10

    def draw_status_info(self, turn, round, layout_name):
        newtime = time.time()
        diff = newtime - self.timestamp
        if diff == 0:
            diff = 0.0000001
        self.fps = (1/diff + (self.FPS_MULT-1) * self.fps)/self.FPS_MULT
        self.timestamp = newtime

        roundturn = "Bot %d / Round % 3d" % (turn, round)

        fps_info = "%.f fps" % self.fps
        self.status_fps_info.config(text=fps_info, )

        self.status_round_info.config(text=roundturn)
        self.status_layout_info.config(text=layout_name)

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
                        justify=tkinter.CENTER, anchor=tkinter.CENTER)

        self.canvas.create_text(center[0] , center[1] ,
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
        self.canvas.delete(tkinter.ALL)

    def resize(self, event):
        # need to be careful not to get negative numbers
        # Tk will crash, if it receives negative numbers
        if event.height > 0:
            self.mesh_graph.screen_width = event.width
            self.mesh_graph.screen_height = event.height
        self.size_changed = True

    def draw_food(self, universe):
        if not self.size_changed:
            return
        self.canvas.delete("food")
        for position in universe.food_list:
            model_x, model_y = position
            food_item = Food(self.mesh_graph, model_x, model_y)
            food_item.draw(self.canvas)

    def draw_maze(self, universe):
        if not self.size_changed:
            return
        self.canvas.delete("wall")
        for position, wall in universe.maze.items():
            model_x, model_y = position
            if wall:
                wall_item = Wall(self.mesh_graph, model_x, model_y)
                wall_item.wall_neighbours = []
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        try:
                            if universe.maze[model_x + dx, model_y + dy]:
                                wall_item.wall_neighbours.append( (dx, dy) )
                        except IndexError:
                            pass
                wall_item.draw(self.canvas)

    def init_bots(self, universe):
        for bot in universe.bots:
            bot_sprite = BotSprite(self.mesh_graph, team=bot.team_index, bot_id=bot.index)

            self.bot_sprites[bot.index] = bot_sprite
            bot_sprite.position = bot.current_pos

    def draw_bots(self, universe, game_state):
        for bot_id, bot_sprite in self.bot_sprites.items():
            say = game_state and game_state["bot_talk"][bot_id]
            bot_sprite.move_to(universe.bots[bot_sprite.bot_id].current_pos, self.canvas, universe, force=self.size_changed, say=say)


class TkApplication:
    def __init__(self, master, address, controller_address=None,
                 geometry=None, delay=1):
        self.master = master
        self.master.configure(background="white")

        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.setsockopt_unicode(zmq.SUBSCRIBE, "")
        self.socket.connect(address)
        self.poll = zmq.Poller()
        self.poll.register(self.socket, zmq.POLLIN)

        if controller_address:
            self.controller_socket = self.context.socket(zmq.DEALER)
            self.controller_socket.connect(controller_address)
        else:
            self.controller_socket = None

        self.frame = tkinter.Frame(self.master, background="white")
        self.master.title("Pelita")

        self.frame.pack(fill=tkinter.BOTH, expand=tkinter.YES)

        self.ui_canvas = UiCanvas(self, geometry=geometry)

        self._min_delay = 1
        self._delay = delay
        self._check_speed_button_state()

        self.running = True

        self.master.bind('q', lambda event: self.quit())
        self.master.createcommand('exit', self.quit)
        self.master.protocol("WM_DELETE_WINDOW", self.quit)

        if self.controller_socket:
            self.master.after_idle(self.request_initial)

    def _after(self, delay, fun, *args):
        """ Execute fun(*args) after delay milliseconds.

        # Patched to quit after `KeyboardInterrupt`s.
        """
        def wrapped_fun():
            try:
                fun(*args)
            except KeyboardInterrupt:
                _logger.info("Detected KeyboardInterrupt. Exiting.")
                self.quit()
        self.master.after(delay, wrapped_fun)

    def toggle_running(self):
        self.running = not self.running
        if self.running:
            self.request_step()

    def read_queue(self):
        try:
            # read all events.
            # if queue is empty, try again in a few ms
            # we don’t want to block here and lock
            # Tk animations
            message = self.socket.recv_unicode(flags=zmq.NOBLOCK)
            message = json.loads(message)
            # we curretly don’t care about the action
            observed = message["__data__"]
            self.observe(observed)

            if self.controller_socket:
                self._after(0 + self._delay, self.request_next, observed)
            else:
                self._after(2 + self._delay, self.read_queue)
            return
        except zmq.ZMQError:
            self.observe({})
            if self.controller_socket:
                self._after(2, self.request_next, {})
            else:
                self._after(2, self.read_queue)

    def request_initial(self):
        if self.controller_socket:
            self.controller_socket.send_json({"__action__": "set_initial"})

        self._after(500, self.request_step)

    def request_next(self, observed):
        if self.running and observed and observed.get("game_state"):
            self.request_step()
        self._after(0, self.read_queue)

    def request_step(self):
        if self.controller_socket:
            self.controller_socket.send_json({"__action__": "play_step"})

    def request_round(self):
        if self.controller_socket:
            self.controller_socket.send_json({"__action__": "play_round"})

    def observe(self, observed):
        universe = observed.get("universe")
        universe = CTFUniverse._from_json_dict(universe) if universe else None
        game_state = observed.get("game_state")

        self.ui_canvas.update(universe, game_state)

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
        self.frame.quit()

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
            # self.ui_canvas.button_game_speed_faster
            # may not be available yet (or may be None).
            # If this is the case, we’ll do nothing at all.
            if self._delay <= self._min_delay:
                self.ui_canvas.button_game_speed_faster.config(state=tkinter.DISABLED)
            else:
                self.ui_canvas.button_game_speed_faster.config(state=tkinter.NORMAL)
        except AttributeError:
            pass
