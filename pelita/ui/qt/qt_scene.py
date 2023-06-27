
from PyQt6 import QtCore, QtGui
from PyQt6.QtCore import QPointF, QRectF
from PyQt6.QtGui import (QColor, QColorConstants, QFont, QPainter,
                         QPainterPath, QPen, QTransform)
from PyQt6.QtWidgets import (QGraphicsEllipseItem, QGraphicsItem,
                             QGraphicsScene, QGraphicsView)

from .qt_items import BotItem, FoodItem, use_painter, ArrowItem
from .qt_pixmaps import generate_wall

import cmath, math

black = QColorConstants.Black
blue_col = QColor(94, 158, 217)
red_col = QColor(235, 90, 90)

class PelitaScene(QGraphicsScene):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.shape = None
        self.walls = []
        self.food = []
        self.food_items = None
        self.arrow = None
        self.bots = []
        self.previous_positions = {}
        self.directions = {}
        self.bot_items = []
        self.shadow_bot_items = []
        self.game_state = {}

        self.grid = False

    def drawBackground(self, painter: QPainter, rect: QRectF) -> None:
        super().drawBackground(painter, rect)

        if not self.shape:
            return

        if self.grid:
            pen = QPen(black)
            pen.setWidth(0) # always 1 pixel regardless of scale
            painter.setPen(pen)
            w, h = self.shape
            for x in range(w + 1):
                painter.drawLine(x, 0, x, h + 1)
            for y in range(h + 1):
                painter.drawLine(0, y, w + 1, y)

        # not the best heuristic but might just do
        dark_mode = self.palette().window().color().lightness() < 100

        generate_wall(painter, self.shape, self.walls, dark_mode=dark_mode)

    def drawForeground(self, painter: QPainter, rect: QRectF):
        super().drawForeground(painter, rect)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        if not self.shape:
            return

        if self.grid:
            # overlay the zone of no noise

            if not self.game_state:
                return
            bot = self.game_state['turn']
            if bot is None:
                # game has not started yet
                return

            try:
                old_pos = tuple(self.game_state['requested_moves'][bot]['previous_position'])
            except TypeError:
                old_pos = self.game_state['bots'][bot]

            def draw_box(pos, fill=None):
                with use_painter(painter) as p:
                    p.translate(pos[0], pos[1])
                    pen = QPen(QColorConstants.Black)
                    pen.setWidthF(0.1)
                    p.setPen(pen)
                    if fill:
                        brush = p.background()
                        brush.setStyle(QtCore.Qt.BrushStyle.BDiagPattern)
                        brush.setColor(fill)
#                        p.setBackground(brush)
                    #p.backgroundMode()

                        p.fillRect(0, 0, 1, 1, brush)
                    else:
                        p.drawRect(0, 0, 1, 1)

                    # else:
                    #     # dx, dy has to be duplicated because the self.screen coordinates go from -1 to 1
                    #     # for the current cell
                    #     dx = (self.req_pos[0] - self.position[0]) * 2
                    #     dy = (self.req_pos[1] - self.position[1]) * 2
                    #     canvas.create_line(self.screen((0, 0)), self.screen((dx, dy)), fill=BROWN,
                    #                                         width=scale, tag=(self.tag, "arrow"), capstyle="round")
                    #     # arrow head
                    #     vector = dx + dy * 1j
                    #     phase = cmath.phase(vector)
                    #     head = vector + cmath.rect(0.1, phase)
                    #     head_left = vector - cmath.rect(1, phase) + cmath.rect(0.9, phase - cmath.pi/4)
                    #     head_right = vector - cmath.rect(1, phase) + cmath.rect(0.9, phase + cmath.pi/4)

                    #     points = [
                    #         self.screen((head_left.real, head_left.imag)),
                    #         self.screen((head.real, head.imag)),
                    #         self.screen((head_right.real, head_right.imag))
                    #     ]
                    #     canvas.create_line(points,
                    #                     fill=BROWN, width=scale, tag=(self.tag, "arrow"), capstyle="round")


            draw_box(old_pos)

            sight_distance = self.game_state["sight_distance"]
            # starting from old_pos, iterate over all positions that are up to sight_distance
            # steps away and put a border around the fields.
            border_cells_relative = set(
                (dx, dy)
                for dx in range(- sight_distance, sight_distance + 1)
                for dy in range(- sight_distance, sight_distance + 1)
                if abs(dx) + abs(dy) == sight_distance
            )

            def in_maze(x, y):
                return 0 <= x < self.game_state['shape'][0] and  0 <= y < self.game_state['shape'][1]

            def on_edge(x, y):
                return x == 0 or x == self.game_state['shape'][0] - 1 or y == 0 or y == self.game_state['shape'][1] - 1


            def draw_line(pos, color, loc):
                pen = QPen(QColorConstants.Black)
                pen.setWidthF(0.1)
                painter.setPen(pen)

                pos = QPointF(pos[0], pos[1])
                loc = QPointF(loc[0], loc[1])
                painter.drawLine(pos, loc)


            STRONG_BLUE = blue_col.darker(20)
            STRONG_RED = red_col.darker(20)

            LIGHT_BLUE = blue_col #.lighter(20)
            LIGHT_RED = red_col #.lighter(20)

            team_col = STRONG_BLUE if bot % 2 == 0 else STRONG_RED

            sight_distance_path = QPainterPath()
            for dx in range(- sight_distance, sight_distance + 1):
                for dy in range(- sight_distance, sight_distance + 1):
                    if abs(dx) + abs(dy) > sight_distance:
                        continue

                    pos = (old_pos[0] + dx, old_pos[1] + dy)
                    if not in_maze(pos[0], pos[1]):
                        continue

                    draw_box(pos, fill=LIGHT_BLUE if bot % 2 == 0 else LIGHT_RED)
                    continue

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
                        if pos[0] == self.game_state['shape'][0] - 1:
                            draw_line(pos, loc=(1, 1, 1, -1), color=team_col)
                        if pos[0] == 0:
                            draw_line(pos, loc=(-1, 1, -1, -1), color=team_col)
                        if pos[1] == self.game_state['shape'][1] - 1:
                            draw_line(pos, loc=(1, 1, -1, 1), color=team_col)
                        if pos[1] == 0:
                            draw_line(pos, loc=(1, -1, -1, -1), color=team_col)



    ### Methods to interact with the scene
    def init_scene(self):

        bot_cols = [
            blue_col,
            red_col,
            blue_col.lighter(110),
            red_col.lighter(110)
        ]

        if not self.food_items:
            if self.food:
                self.food_items = {tuple(pos): FoodItem(pos, blue_col if pos[0] < self.shape[0] / 2 else red_col) for pos in self.food}
                for pos, item in self.food_items.items():
                    self.addItem(item)

        if not self.bot_items:
            if self.bots:
                self.bot_items = [BotItem(bot_cols[idx]) for idx, pos in enumerate(self.bots)]
                for item in self.bot_items:
                    item.bot_type = "D"
                    item.direction = (0, 0)
                    item.setPos(30, 20)
                    self.addItem(item)
                self.shadow_bot_items = [BotItem(bot_cols[idx], shadow=True) for idx, pos in enumerate(self.bots)]
                for item in self.shadow_bot_items:
                    item.bot_type = "D"
                    item.direction = (0, 0)
                    item.setPos(30, 20)
                    self.addItem(item)

    def move_bot(self, bot_idx, pos):
        item = self.bot_items[bot_idx]

        # requested_moves[idx] may be None!
        if prev_pos := self.requested_moves[bot_idx] and self.requested_moves[bot_idx]['previous_position']:
            direction = pos[0] - prev_pos[0], pos[1] - prev_pos[1]
            #print(idx, prev_pos, bot, pos, direction)
        else:
            direction = (0, 1)

        if bot_idx % 2 == 0:
            item.direction = direction
            if pos[0] < self.shape[0] / 2:
                item.bot_type = "D"
            else:
                item.bot_type = "H"

        else:
            item.direction = direction
            if pos[0] < self.shape[0] / 2:
                item.bot_type = "H"
            else:
                item.bot_type = "D"

        item.move_to(prev_pos, pos, animate=bot_idx==self.game_state['turn'])


    def update_arrow(self):
        bot = self.game_state['turn']
        if bot is None:
            return

        try:
            old_pos = tuple(self.game_state['requested_moves'][bot]['previous_position'])
        except TypeError:
            old_pos = self.game_state['bots'][bot]

        BROWN = QColor(48, 26, 22)
        if not self.arrow:
            self.arrow  = ArrowItem(old_pos, BROWN, self.game_state['bots'][bot], old_pos, success=self.game_state['requested_moves'][bot]['success'])
            self.addItem(self.arrow)
        else:
            self.arrow.move(old_pos, BROWN, self.game_state['bots'][bot], old_pos, success=self.game_state['requested_moves'][bot]['success'])
        self.show_grid()

    def show_grid(self):
        if not self.arrow:
            return

        if self.grid:
            self.arrow.show()
        else:
            self.arrow.hide()

    def hide_food(self, pos):
        if pos in self.food_items:
            self.food_items[pos].hide()
