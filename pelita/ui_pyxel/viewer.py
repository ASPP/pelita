import pyxel
import zmq
import json

# scale of one tile
SCALE = 16

# sprite constants
SPRITES = "sprites.pyxres"
IMG = 0
SPRITE_GHOST_BLUE = (0, 0)
SPRITE_GHOST_RED = (16, 0)
SPRITE_PACMAN_BLUE = (0, 16)
SPRITE_PACMAN_RED = (16, 16)
SPRITE_FOOD_BLUE = (0, 32)
SPRITE_FOOD_RED = (16, 32)
SPRITE_BORDER_BLUE = (0, 48)
SPRITE_BORDER_RED = (16, 48)

WALL_IMG_BANK = 1
WALL_CENTER = (0, 0)
WALL_FILL = (16, 0)

def scale(t, s):
    return t[0] * s, t[1] * s

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
        self.shape = self.layout["shape"]
        self.flip = [1] * 4
        self.rotate = [0] * 4

        pyxel.init(*scale(self.shape, SCALE))

        pyxel.load(SPRITES)

        pyxel.mouse(visible=True)
        pyxel.run(self.update, self.draw)

    def _update(self, timeout=0):
        incoming = self.socket.poll(timeout)
        if incoming == zmq.POLLIN:
            msg = self.socket.recv_unicode()
            msg = json.loads(msg)

            if msg["__action__"] == "observe":
                self.layout = msg["__data__"]
                self.history.append(self.layout)

    def update(self):
        self._update()

    def draw(self):
        # background color, "clear screen"
        pyxel.cls(pyxel.COLOR_WHITE)

        self.draw_walls()
        self.draw_border()
        self.draw_food()
        self.draw_bots()

    def draw_walls(self):
        walls = self.layout["walls"]
        steps = ((0, 1), (-1, 0), (0, -1), (1, 0))
        rotations = (0, 90, 180, 270)

        for wall in walls:
            for step, rotate in zip(steps, rotations):
                neighbor = [wall[0] + step[0], wall[1] + step[1]]

                if neighbor[0] < 0 or neighbor[0] > self.shape[0] - 1 or neighbor[1] < 0 or neighbor[1] > self.shape[1] - 1:
                    continue

                if neighbor in walls:
                    pyxel.blt(*scale(neighbor, SCALE), WALL_IMG_BANK, *WALL_FILL, SCALE, SCALE, pyxel.COLOR_WHITE, rotate)

            pyxel.blt(*scale(wall, SCALE), WALL_IMG_BANK, *WALL_CENTER, SCALE, SCALE, pyxel.COLOR_WHITE)

    def draw_border(self):
        walls = self.layout["walls"]

        for row in range(self.shape[1]):
            blue = [self.shape[0] // 2 - 1, row]
            red = [self.shape[0] // 2, row]

            if blue not in walls:
                pyxel.blt(*scale(blue, SCALE), IMG, *SPRITE_BORDER_BLUE, SCALE, SCALE, pyxel.COLOR_BLACK)

            if red not in walls:
                pyxel.blt(*scale(red, SCALE), IMG, *SPRITE_BORDER_RED, SCALE, SCALE, pyxel.COLOR_BLACK)
                

    def draw_food(self):
        foods = self.layout["food"]

        for food in foods:
            if food[0] < self.shape[0] // 2:
                sprite = SPRITE_FOOD_BLUE
            else:
                sprite = SPRITE_FOOD_RED
            pyxel.blt(*scale(food, SCALE), IMG, *sprite, SCALE, SCALE, pyxel.COLOR_BLACK)
        
    def draw_bots(self):
        positions = self.layout["bots"]  # a, x, b, y; blue: a, b; red: x, y
        moves = self.layout["requested_moves"]

        for bot, (pos, move) in enumerate(zip(positions, moves)):
            sprite, flip, rotate = self._sprite(bot, pos, move)
            pyxel.blt(*scale(pos, SCALE), IMG, *sprite, flip * SCALE, SCALE, pyxel.COLOR_BLACK, rotate)


    def _sprite(self, bot: int, pos: tuple[int, int], move: None | dict) -> tuple[tuple[int, int], int, int]:
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
