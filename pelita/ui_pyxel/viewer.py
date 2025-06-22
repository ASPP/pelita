import pyxel
import zmq
import json

# scale of one tile
SCALE = 16
HEADER = 4
FOOTER = 3

# sprite constants
RESOURCES = "resources.pyxres"
SPRITE_BANK = 0
SPRITE_GHOST_BLUE = (0, 0)
SPRITE_GHOST_RED = (16, 0)
SPRITE_PACMAN_BLUE = (0, 16)
SPRITE_PACMAN_RED = (16, 16)
SPRITE_FOOD_BLUE = (0, 32)
SPRITE_FOOD_RED = (16, 32)
SPRITE_BORDER_BLUE = (0, 48)
SPRITE_BORDER_RED = (16, 48)

WALL_BANK = 1
WALL_CENTER = (0, 0)
WALL_FILL = (16, 0)

ICON_BANK = 2
ICON_ERROR = (0, 0)
ICON_KILL = (16, 0)
ICON_DEATH = (32, 0)
ICON_TIME = (48, 0)
ICON_ROUND = (64, 0)
ICON_REWIND = (0, 16)
ICON_PLAY_PAUSE = (16, 16)
ICON_FORWARD = (32, 16)
ICON_SLOWER = (0, 32)
ICON_FASTER = (16, 32)


def mul(t, s):
    return t[0] * s, t[1] * s

def add(a, b):
    return a[0] + b[0], a[1] + b[1]

def sub(b, a):
    return b[0] - a[0], b[1] - a[1]


def align_left(obj, ref, off):
    return off

def align_middle(obj, ref, off):
    return ref // 2 - obj // 2 + off

def align_right(obj, ref, off):
    return ref - obj + off

def align(aligns, obj, *refs):
    return tuple(
        _align(obj, ref, off)
        for _align, obj, (ref, off) in zip(aligns, obj, refs)
    )

def align_top_left(obj, *refs):
    # width: left, height: left
    return align((align_left, align_left), obj, *refs)

def align_top_middle(obj, *refs):
    # width: middle, height: left
    return align((align_middle, align_left), obj, *refs)

def align_top_right(obj, *refs):
    # width: right, height: left
    return align((align_right, align_left), obj, *refs)

def align_middle_left(obj, *refs):
    # width: left, height: middle
    return align((align_left, align_middle), obj, *refs)

def align_middle_middle(obj, *refs):
    # width: middle, height: middle
    return align((align_middle, align_middle), obj, *refs)

def align_middle_right(obj, *refs):
    # width: right, height: middle
    return align((align_right, align_middle), obj, *refs)

def align_bottom_left(obj, *refs):
    # width: left, height: right
    return align((align_left, align_right), obj, *refs)

def align_bottom_middle(obj, *refs):
    # width: middle, height: right
    return align((align_middle, align_right), obj, *refs)

def align_bottom_right(obj, *refs):
    # width: right, height: right
    return align((align_right, align_right), obj, *refs)


class App:
    def __init__(self):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.setsockopt_unicode(zmq.SUBSCRIBE, "")
        self.socket.bind("tcp://127.0.0.1:8888")
        self.poll = zmq.Poller()
        self.poll.register(self.socket, zmq.POLLIN)

        # get shape
        self.history = list()
        self._update(-1)
        self.shape = self.game_state["shape"]
        self.flip = [1] * 4
        self.rotate = [0] * 4

        maze_size = add((2, 2), self.shape)
        canvas = (maze_size[0], HEADER + maze_size[1] + FOOTER)
        self.canvas = mul(canvas, SCALE)
        self.header = (self.canvas[0], HEADER * SCALE)
        self.maze = (self.canvas[0], maze_size[1] * SCALE)
        self.footer = (self.canvas[0], FOOTER * SCALE)

        pyxel.init(*self.canvas, capture_sec=10000)

        self.font8 = pyxel.Font("./ib8x16u.bdf")
        self.font16 = pyxel.Font("./ib16x16u.bdf")

        pyxel.load(RESOURCES)

        pyxel.mouse(visible=True)
        pyxel.run(self.update, self.draw)

    def _update(self, timeout=0):
        incoming = self.socket.poll(timeout)
        if incoming == zmq.POLLIN:
            msg = self.socket.recv_unicode()
            msg = json.loads(msg)

            if msg["__action__"] == "observe":
                self.game_state = msg["__data__"]
                self.history.append(self.game_state)

    def update(self):
        self._update()

    def draw(self):
        # background color, "clear screen"
        pyxel.cls(pyxel.COLOR_WHITE)

        self.draw_header()
        self.draw_walls()
        self.draw_border()
        self.draw_food()
        self.draw_bots()

        if self.game_state["gameover"]:
            print(self.game_state)
            self.draw_game_over()

    def draw_header(self):
        GS = self.game_state

        blue_team_name, red_team_name = GS["team_names"]
        blue_team_name = blue_team_name or ""
        red_team_name = red_team_name or ""
        blue_score, red_score = GS["score"]
        blue_score = str(blue_score)
        red_score = str(red_score)

        score_line_ref = (
            (self.header[0], 0),
            (self.header[1] // 2, 0)
        )
        team_name_line_ref = (
            (self.header[0], 0),
            (self.header[1] // 4, self.header[1] // 2)
        )
        team_stats_line_ref = (
            (self.header[0], 0),
            (self.header[1] // 4, (self.header[1] * 3) // 4)
        )


        # score
        score = "000:000"
        score_width = self.font16.text_width(score)

        score_ref_dims = (score_width, SCALE)
        score_ref_shift = align_middle_middle(score_ref_dims, *score_line_ref)

        score_ref = tuple(zip(score_ref_dims, score_ref_shift))

        blue_dims = (self.font16.text_width(blue_score), SCALE)
        blue_shift = align_bottom_left(blue_dims, *score_ref)
        
        colon_dims = (self.font16.text_width(":"), SCALE)
        colon_shift = align_middle_middle(colon_dims, *score_ref)

        red_dims = (self.font16.text_width(red_score), SCALE)
        red_shift = align_bottom_right(red_dims, *score_ref)

        pyxel.text(*blue_shift, blue_score, pyxel.COLOR_DARK_BLUE, self.font16)
        pyxel.text(*colon_shift, ":", pyxel.COLOR_BLACK, self.font16)
        pyxel.text(*red_shift, red_score, pyxel.COLOR_RED, self.font16)


        # team names
        blue_team_dims = (self.font8.text_width(blue_team_name), SCALE)
        blue_team_shift = align_middle_left(blue_team_dims, *team_name_line_ref)

        red_team_dims = (self.font8.text_width(red_team_name), SCALE)
        red_team_shift = align_middle_right(red_team_dims, *team_name_line_ref)
        
        pyxel.text(*blue_team_shift, blue_team_name, pyxel.COLOR_DARK_BLUE, self.font8)
        pyxel.text(*red_team_shift, red_team_name, pyxel.COLOR_RED, self.font8)

        # progress
        round = GS["round"] or "---"
        max_rounds = GS["max_rounds"]

        progress_str_template = f" {max_rounds}/{max_rounds}"
        progress_str = f" {round}/{max_rounds}"

        progress_str_width = self.font8.text_width(progress_str_template)
        progress_ref_dims = (SCALE + progress_str_width, SCALE)
        progress_ref_shift = align_middle_middle(progress_ref_dims, *team_stats_line_ref)

        progress_ref = tuple(zip(progress_ref_dims, progress_ref_shift))

        progress_icon_dims = (SCALE, SCALE)
        progress_icon_shift = align_middle_left(progress_icon_dims, *progress_ref)

        pyxel.blt(*progress_icon_shift, ICON_BANK, *ICON_ROUND, SCALE, SCALE, pyxel.COLOR_WHITE)

        progress_str_dims = (self.font8.text_width(progress_str), SCALE)
        progress_str_shift = align_middle_right(progress_str_dims, *progress_ref)

        pyxel.text(*progress_str_shift, progress_str, pyxel.COLOR_BLACK, self.font8)


        # team stats
        errors = GS["errors"]
        blue_errors = errors[0] or 0
        red_errors = errors[1] or 0

        kills = GS["kills"]
        deaths = GS["deaths"]

        blue_kills = kills[0] + kills[2]
        red_kills = kills[1] + kills[3]

        blue_deaths = deaths[0] + deaths[1]
        red_deaths = deaths[1] + deaths[3]

        blue_time, red_time = GS["team_time"]

        blue_stats = f" {blue_errors} {blue_kills} {blue_deaths} {blue_time:.2f}"
        red_stats = f" {red_errors} {red_kills} {red_deaths} {red_time:.2f}"

        blue_stats_dims = (self.font8.text_width(blue_stats), SCALE)
        blue_stats_shift = align_middle_left(blue_stats_dims, *team_stats_line_ref)

        red_stats_dims = (self.font8.text_width(red_stats), SCALE)
        red_stats_shift = align_middle_right(red_stats_dims, *team_stats_line_ref)

        pyxel.text(*blue_stats_shift, blue_stats, pyxel.COLOR_BLACK, self.font8)
        pyxel.text(*red_stats_shift, red_stats, pyxel.COLOR_BLACK, self.font8)



    def draw_walls(self):
        walls = self.game_state["walls"]
        steps = ((0, 1), (-1, 0), (0, -1), (1, 0))
        rotations = (0, 90, 180, 270)

        for wall in walls:
            for step, rotate in zip(steps, rotations):
                neighbor = [wall[0] + step[0], wall[1] + step[1]]

                if (
                    neighbor[0] < 0
                    or neighbor[0] > self.shape[0] - 1
                    or neighbor[1] < 0
                    or neighbor[1] > self.shape[1] - 1
                ):
                    continue

                if neighbor in walls:
                    pyxel.blt(
                        *add((SCALE, self.header[1] + SCALE), mul(neighbor, SCALE)),
                        WALL_BANK,
                        *WALL_FILL,
                        SCALE,
                        SCALE,
                        pyxel.COLOR_WHITE,
                        rotate,
                    )

            pyxel.blt(
                *add((SCALE, self.header[1] + SCALE), mul(wall, SCALE)),
                WALL_BANK,
                *WALL_CENTER,
                SCALE,
                SCALE,
                pyxel.COLOR_WHITE,
            )

    def draw_border(self):
        walls = self.game_state["walls"]

        for row in range(self.shape[1]):
            blue = [self.shape[0] // 2 - 1, row]
            red = [self.shape[0] // 2, row]

            if blue not in walls:
                pyxel.blt(
                    *add((SCALE, self.header[1] + SCALE), mul(blue, SCALE)),
                    SPRITE_BANK,
                    *SPRITE_BORDER_BLUE,
                    SCALE,
                    SCALE,
                    pyxel.COLOR_BLACK,
                )

            if red not in walls:
                pyxel.blt(
                    *add((SCALE, self.header[1] + SCALE), mul(red, SCALE)),
                    SPRITE_BANK,
                    *SPRITE_BORDER_RED,
                    SCALE,
                    SCALE,
                    pyxel.COLOR_BLACK,
                )

    def draw_food(self):
        foods = self.game_state["food"]

        for food in foods:
            if food[0] < self.shape[0] // 2:
                sprite = SPRITE_FOOD_BLUE
            else:
                sprite = SPRITE_FOOD_RED
            pyxel.blt(
                *add((SCALE, self.header[1] + SCALE), mul(food, SCALE)), SPRITE_BANK, *sprite, SCALE, SCALE, pyxel.COLOR_BLACK
            )

    def draw_bots(self):
        positions = self.game_state["bots"]  # a, x, b, y; blue: a, b; red: x, y
        moves = self.game_state["requested_moves"]

        for bot, (pos, move) in enumerate(zip(positions, moves)):
            sprite, flip, rotate = self._get_bot_sprite(bot, pos, move)
            pyxel.blt(
                *add((SCALE, self.header[1] + SCALE), mul(pos, SCALE)),
                SPRITE_BANK,
                *sprite,
                flip * SCALE,
                SCALE,
                pyxel.COLOR_BLACK,
                rotate,
            )

    def draw_game_over(self):
        gs = self.game_state
        winner = gs["whowins"]
        if winner is not None:
            if winner == 0:
                winner_color = pyxel.COLOR_DARK_BLUE
            elif winner == 1:
                winner_color = pyxel.COLOR_RED
            winner = "{} WIN".format(gs["team_names"][winner])
        else:
            winner_color = pyxel.COLOR_YELLOW
            winner = "DRAW"

        heading = "GAME OVER"

        heading_dim = (self.font16.text_width(heading), SCALE)
        heading_shift = align_bottom_middle(heading_dim, (self.canvas[0], 0), (self.canvas[1] // 2, 0))

        winner_dim = (self.font16.text_width(winner), SCALE)
        winner_shift = align_top_middle(winner_dim, (self.canvas[0], 0), (self.canvas[1] // 2, self.canvas[1] // 2))
        
        pyxel.text(*heading_shift, heading, pyxel.COLOR_YELLOW, self.font16)
        pyxel.text(*winner_shift, winner, winner_color, self.font16)

    def _get_bot_sprite(
        self, bot: int, pos: tuple[int, int], move: None | dict
    ) -> tuple[tuple[int, int], int, int]:
        ## sprites
        # blue
        if bot in (0, 2):
            in_homezone = pos[0] < self.shape[0] // 2
            if in_homezone:
                sprite = SPRITE_GHOST_BLUE
            else:
                sprite = SPRITE_PACMAN_BLUE
        # red
        elif bot in (1, 3):
            in_homezone = pos[0] >= self.shape[0] // 2
            if in_homezone:
                sprite = SPRITE_GHOST_RED
            else:
                sprite = SPRITE_PACMAN_RED

        ## diff
        if move is None:
            diff = (0, 0)
        else:
            before = move["previous_position"]
            diff = pos[0] - before[0], pos[1] - before[1]

        ## horizontal flipping
        if diff[0] > 0:
            flip = 1
        elif diff[0] < 0:
            flip = -1
        else:
            flip = self.flip[bot]

        ## rotation
        if in_homezone:  # i.e. ghost sprite
            rotate = 0
        else:
            if diff[0] == 0:
                if diff[1] > 0:
                    rotate = 90
                elif diff[1] < 0:
                    rotate = -90
                else:
                    rotate = self.rotate[bot]
            else:
                rotate = 0

        # update last used values
        self.flip[bot] = flip
        self.rotate[bot] = rotate

        return sprite, flip, rotate


if __name__ == "__main__":
    App()
