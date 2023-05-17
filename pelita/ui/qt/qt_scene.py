
from PyQt6 import QtCore, QtGui
from PyQt6.QtCore import QPointF, QRectF
from PyQt6.QtGui import (QColor, QColorConstants, QFont, QPainter,
                         QPainterPath, QPen, QTransform)
from PyQt6.QtWidgets import (QGraphicsEllipseItem, QGraphicsItem,
                             QGraphicsScene, QGraphicsView)

from .qt_items import BotItem, FoodItem
from .qt_pixmaps import generate_wall

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
        self.bots = []
        self.previous_positions = {}
        self.directions = {}
        self.bot_items = []

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

        if not self.shape:
            return

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

        item.setPos(pos[0], pos[1])

    def hide_food(self, pos):
        if pos in self.food_items:
            self.food_items[pos].hide()
