
import cmath
import math
from contextlib import contextmanager

from PyQt6 import QtCore
from PyQt6.QtCore import QPointF, QRectF
from PyQt6.QtGui import (QColor, QColorConstants, QFont, QPainter,
                         QPainterPath, QPen)
from PyQt6.QtWidgets import QGraphicsItem

black = QColorConstants.Black

@contextmanager
def use_painter(painter: QPainter):
    # this should automatically ensure that a painter used in a
    # trafo is cleaned up after (in case we want to catch an exception)
    # not sure if this is working as expected in all cases
    painter.save()
    try:
        yield painter
    finally:
        painter.restore()

def de_casteljau_2d(t, coefs):
    # given coefficients [ax, ay, bx, by, ...] for a bezier curve [0, 1]
    # return coefficients for a bezier curve [t, 1]

    beta = list(coefs) # values in this list are overridden
    n = len(beta) // 2
    for j in range(1, n):
        for k in range(n - j):
            beta[2 * k]     = beta[2 * k]     * (1 - t) + beta[2 * (k + 1)]     * t
            beta[2 * k + 1] = beta[2 * k + 1] * (1 - t) + beta[2 * (k + 1) + 1] * t
    return beta

def pairwise_reverse(iterable):
    # reverse [ax, ay, bx, by, ..., zx, zy] pairwise to
    # [zx, xy, ..., bx, by, ax, ay]

    def gen():
        for i in reversed(range(len(iterable) // 2)):
            yield iterable[i * 2]
            yield iterable[i * 2 + 1]
    return list(gen())

def de_casteljau_2d_reversed(t, coefs):
    # given coefficients [ax, ay, bx, by, ...] for a bezier curve [0, 1]
    # return coefficients for a bezier curve [0, t]
    return pairwise_reverse(de_casteljau_2d(t, pairwise_reverse(coefs)))


class FoodItem(QGraphicsItem):
    def __init__(self, pos, color, parent=None):
        super().__init__(parent)
        self.setPos(pos[0] + 0.5, pos[1] + 0.5)
        self.color = color

    def paint(self, painter: QPainter, option, widget):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(self.color)
        painter.setPen(QPen(black, 0.02))

        painter.drawEllipse(QRectF(-0.2, -0.2, 0.4, 0.4))

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, 1, 1)


class BotItem(QGraphicsItem):
    def __init__(self, color, parent=None):
        super().__init__(parent)
        self.color = color
        self.bot_type = "D"

    def boundingRect(self):
        # Bounding rect must be a little bigger for the outline
        return QRectF(-0.02, -0.02, 1.02, 1.02)

    def paint(self, painter: QPainter, option, widget):
        if self.bot_type == "D":
            paint_destroyer(painter, self.color, self.direction)
        else:
            paint_harvester(painter, self.color, self.direction)


def paint_destroyer(painter: QPainter, color, direction):

    h = 0.3 # the amplitude of the ‘feet’. higher -> more kraken-like
    knee_y = 7/8 # y-position of the knees
    cx = 0.5 # how much the feet are slanted. could be used in animation

    # number of full bezier curves = number of bumps between feet
    n_bumps = 3
    n_parts = n_bumps * 2 + 1

    # bezier coeffcients
    sine_like_bezier = [0, knee_y, cx, knee_y + h, 1 - cx, knee_y - h, 1, knee_y]
    # quarter = de_casteljau_2d(3/4, sine_like_bezier)
    half_bezier = de_casteljau_2d_reversed(1/2, sine_like_bezier)

    sx, sy, c1x, c1y, c2x, c2y, ex, ey = sine_like_bezier

    # start a new path
    path = QPainterPath(QPointF(sx, sy))

    for i in range(n_bumps):
        # we need to shrink the curve in the width dimension
        # and offset it accordingly
        offsetx = (2 * i) / n_parts

        c1x = 2 * sine_like_bezier[2] / n_parts + offsetx
        c1y = sine_like_bezier[3]

        c2x = 2 * sine_like_bezier[4] / n_parts + offsetx
        c2y = sine_like_bezier[5]

        ex = 2 * sine_like_bezier[6] / n_parts + offsetx
        ey = sine_like_bezier[7]

        path.cubicTo(c1x, c1y, c2x, c2y, ex, ey)

    # half bezier curve that is missing
    offsetx = (n_parts - 1) / n_parts
    c1x = 2 * half_bezier[2] / n_parts + offsetx
    c1y = half_bezier[3]

    c2x = 2 * half_bezier[4] / n_parts + offsetx
    c2y = half_bezier[5]

    ex = 2 * half_bezier[6] / n_parts + offsetx
    ey = half_bezier[7]
    path.cubicTo(c1x, c1y, c2x, c2y, ex, ey)

    # ghost head

    path.lineTo(1, knee_y)
    path.lineTo(1, 0.5)
    path.cubicTo(1, -0.15, 0, -0.15, 0, 0.5)
    path.closeSubpath()

    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(color)
    painter.setOpacity(0.9) # Ghosts are a little transparent
    painter.setPen(QPen(black, 0.02))

    painter.drawPath(path)

    draw_eye(painter, 0.3, 0.3)
    draw_eye(painter, 0.7, 0.3)


def paint_harvester(painter: QPainter, color, direction):
    rotation = math.degrees(cmath.phase(direction[0] - direction[1]*1j))
    # ensure that the eye is never at the bottom
    if 179 < rotation < 181:
        flip_eye = True
    else:
        flip_eye = False

    bounding_rect = QRectF(0, 0, 1, 1)
    # bot body
    path = QPainterPath(QPointF(0.5, 0.5))
    path.arcTo(bounding_rect, 20, 320)
    path.closeSubpath()

    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(color)
    painter.setPen(QPen(black, 0.02))

    # rotate around the 0.5, 0.5 centre point
    painter.translate(0.5, 0.5)
    painter.rotate(-rotation)
    painter.translate(-0.5, -0.5)

    painter.drawPath(path)
    if not flip_eye:
        draw_eye(painter, 0.7, 0.2)
    else:
        draw_eye(painter, 0.7, 0.8)



def draw_eye(painter, x, y):
    # draw an eye to (relative) location x, y
    # assumes that the painter has been trafo’d to a position already
    with use_painter(painter) as p:
        # eyes
        eye_size = 0.1
        p.setBrush(QColor(235, 235, 30))
        p.drawEllipse(QRectF(x - eye_size, y - eye_size, eye_size * 2, eye_size * 2))

class EndTextOverlay(QGraphicsItem):
    def __init__(self, text, parent: QGraphicsItem = None) -> None:
        super().__init__(parent)
        self.text = text

    def boundingRect(self):
        return QRectF(1, 1, 121, 81)

    def paint(self, painter: QPainter, option, widget):
        fill = QColor("#FFC903")
        outline = QColor("#ED1B22")

        font = QFont(["Courier", "Courier New"])

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.scale(1/6, 1/6)

        painter.setBrush(outline)
        painter.setFont(font)


        # TODO This should be done with a path and outline (drawText cannot do that)
        painter.setPen(QPen(outline, 2))
        for i in [-2, -1, 0, 1, 2]:
            for j in [-2, -1, 0, 1, 2]:
                painter.drawText(QRectF(i * 0.3, j * 0.3, 220, 80), QtCore.Qt.AlignmentFlag.AlignCenter, self.text)

        painter.setPen(QPen(fill, 2))
        painter.drawText(QRectF(0, 0, 220, 80), QtCore.Qt.AlignmentFlag.AlignCenter, self.text)

