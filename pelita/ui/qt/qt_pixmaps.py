
from PyQt6 import QtCore, QtGui
from PyQt6.QtCore import QPointF, QRectF
from PyQt6.QtGui import QBrush, QPainter, QPen


def generate_wall(painter: QPainter, shape, walls, dark_mode=True):
    maze = [tuple(pos) for pos in walls]
    width, height = shape

    painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
    #painter.scale(12, 12)

    pen_size = 0.05
    painter.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0), pen_size))

    blue_col = QtGui.QColor(94, 158, 217)
    red_col = QtGui.QColor(235, 90, 90)
    brown_col = QtGui.QColor(48, 26, 22)

    def move_pos(a, b):
        ax, ay = a
        bx, by = b
        return (ax + bx, ay + by)

    if not dark_mode:
        pen_size = 0.6
        painter.setPen(QPen(brown_col, pen_size, cap=QtCore.Qt.PenCapStyle.RoundCap))
        painter.setBrush(QBrush(brown_col, QtCore.Qt.BrushStyle.SolidPattern))

        for position in maze:
            painter.save()
            painter.translate(position[0] + 0.5, position[1] + 0.5)

            x, y = position
            neighbors = [(dx, dy)
                          for dx in [-1, 0, 1]
                          for dy in [-1, 0, 1]
                          if (x + dx, y + dy) in maze]

            if not ((0, 1) in neighbors or
                    (1, 0) in neighbors or
                    (0, -1) in neighbors or
                    (-1, 0) in neighbors):
                # if there is no direct neighbour, we can’t connect.
                # draw only a small dot.
                # TODO add diagonal lines

                painter.drawLine(QPointF(-0.3, 0), QPointF(0.3, 0))

            else:
                neighbors_check = [(-1, -1), (0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0)]
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        if (dx, dy) in neighbors:
                            if dx == dy == 0:
                                continue
                            if dx * dy != 0:
                                continue
                            index = neighbors_check.index((dx, dy))
                            if (neighbors_check[(index + 1) % len(neighbors_check)] in neighbors and
                                neighbors_check[(index - 1) % len(neighbors_check)] in neighbors):
                                pass
                            else:
                                painter.drawLine(QPointF(0, 0), QPointF(dx, dy))

                # if we are drawing a closed square, fill in the internal part
                # detect the square when we are on the bottom-left vertex of it
                square_neighbors = {(0,0), (0,-1), (1,0), (1,-1)}
                if square_neighbors <= set(neighbors):
                    painter.drawRect(QRectF(0, 0, 1, -1))


            painter.restore()

    else:

        for position in maze:

            if position[0] < width / 2:
                painter.setPen(QtGui.QPen(blue_col, pen_size))
                painter.setBrush(blue_col)
            else:
                painter.setPen(QtGui.QPen(red_col, pen_size))
                painter.setBrush(red_col)

            rot_moves = [(0,   [(-1,  0), (-1, -1), ( 0, -1)]),
                        (90,  [( 0, -1), ( 1, -1), ( 1,  0)]),
                        (180, [( 1,  0), ( 1,  1), ( 0,  1)]),
                        (270, [( 0,  1), (-1,  1), (-1,  0)])]

            for rot, moves in rot_moves:
                # we center on the middle point of the square
                painter.save()
                painter.translate(position[0] + 0.5, position[1] + 0.5)
                painter.rotate(rot)

                wall_moves = [move for move in moves if move_pos(position, move) in maze]

                left, topleft, top, *remainder = moves

                if left in wall_moves and top not in wall_moves:
                    painter.drawLine(QPointF(-0.5, -0.3), QPointF(0, -0.3))


                elif left in wall_moves and top in wall_moves and not topleft in wall_moves:
                    painter.drawArc(QRectF(-0.7, -0.7, 0.4, 0.4), 0 * 16, -90 * 16)

                elif left in wall_moves and top in wall_moves and  topleft in wall_moves:
                    pass

                elif left not in wall_moves and top not in wall_moves:
                    painter.drawArc(QRectF(-0.3, -0.3, 0.6, 0.6), 90 * 16, 90 * 16)

                elif left not in wall_moves and top in wall_moves:
                    painter.drawLine(QPointF(-0.3, -0.5), QPointF(-0.3, 0))

                painter.restore()

