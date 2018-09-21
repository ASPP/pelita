
from ...graph import move_pos

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QRectF, QPointF

def generate_wall(maze, QWidget):
    pixmap = QtGui.QPixmap(QWidget.width() * 2, QWidget.height() * 2)
    pixmap.fill(QtCore.Qt.white)
    pixmap.setDevicePixelRatio(2.0)

    universe_width = QWidget.universe.maze.width
    universe_height = QWidget.universe.maze.height
    painter = QtGui.QPainter(pixmap)
    painter.setRenderHint(QtGui.QPainter.Antialiasing)
    width = QWidget.width() 
    height = QWidget.height() 

    painter.scale(width / universe_width, height / universe_height)
    pen_size = 0.05
    painter.setPen(QtGui.QPen(QtCore.Qt.black, pen_size))

    blue_col = QtGui.QColor(94, 158, 217)
    red_col = QtGui.QColor(235, 90, 90)

    # to draw the border, we start on an unvisited wall position,
    # that is surrounded by at least one square of free space.
    # we then follow the outline clockwise and counterclockwise
    visited = set()
    start = (0, 0)
    position = start
#    path = QtGui.QPainterPath(QPointF(position[0] + 0.2, position[1] + 0.2))

    for position, value in maze.items():
        if position[0] < QWidget.universe.maze.width / 2:
            #brush = QtGui.QBrush(blue_col, QtCore.Qt.Dense4Pattern)
            painter.setPen(QtGui.QPen(blue_col, pen_size))
        else:
            painter.setPen(QtGui.QPen(red_col, pen_size))
        if not value: continue

        rot_moves = [(0,   [(-1,  0), (-1, -1), ( 0, -1)]),
                     (90,  [( 0, -1), ( 1, -1), ( 1,  0)]),
                     (180, [( 1,  0), ( 1,  1), ( 0,  1)]),
                     (270, [( 0,  1), (-1,  1), (-1,  0)])]

        for rot, moves in rot_moves:
            # we center on the middle point of the square
            painter.save()
            painter.translate(position[0] + 0.5, position[1] + 0.5)
            painter.rotate(rot)

            wall_moves = [move for move in moves
                if move_pos(position, move) in maze and maze[move_pos(position, move)]]
            
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

#        if (0, -1) in wall_moves and not (1, -1) in wall_moves and (1, 0) in wall_moves:
#            painter.drawArc(QRectF(position[0] + 0.7, position[1] + 0.3, 0.6, -0.6), 180 * 16, 90 * 16)
#        elif (0, -1) in wall_moves and not (1, 0) in wall_moves and (0, 1) in wall_moves:
#            painter.drawLine(QPointF(position[0] + 0.7, position[1] + 0), QPointF(position[0] + 0.7, position[1] + 1))
#        elif (0, -1) not in wall_moves and not (1, 0) in wall_moves and (0, 1) in wall_moves:
#            painter.drawArc(QRectF(position[0] + 0.1, position[1] + 0.3, 0.6, 0.6), 16, 90 * 16)

#        visited.add(position)
#        top_neighbor = move_pos(position, (0, -1))
#        bottom_neighbor = move_pos(position, (0, 1))
#        left_neighbor = move_pos(position, (-1, 0))
#        right_neighbor = move_pos(position, (1, 0))
#        print(top_neighbor, bottom_neighbor, left_neighbor, right_neighbor)
#        if top_neighbor in maze and maze[top_neighbor] and not top_neighbor in visited:
#            path.lineTo(top_neighbor[0] + 0.2, top_neighbor[1] + 0.8)
#            position = top_neighbor
#        elif right_neighbor in maze and maze[right_neighbor] and not right_neighbor in visited:
#            path.lineTo(right_neighbor[0] + 0.2, right_neighbor[1] + 0.8)
#            position = right_neighbor
#        elif bottom_neighbor in maze and maze[bottom_neighbor] and not bottom_neighbor in visited:
#            path.lineTo(bottom_neighbor[0] + 0.2, bottom_neighbor[1] + 0.8)
#            position = bottom_neighbor
#        elif left_neighbor in maze and maze[left_neighbor] and not left_neighbor in visited:
#            path.lineTo(left_neighbor[0] + 0.2, left_neighbor[1] + 0.8)
#            position = left_neighbor

#    painter.drawPath(path)

    for position, wall in maze.items():
        if wall:
            if position[0] < QWidget.universe.maze.width / 2:
                brush = QtGui.QBrush(blue_col, QtCore.Qt.Dense4Pattern)
                inverted = painter.worldTransform().inverted()
                brush.setTransform(inverted[0])
                painter.setBrush(brush)
            else:
                brush = QtGui.QBrush(red_col, QtCore.Qt.Dense4Pattern)
                inverted = painter.worldTransform().inverted()
                brush.setTransform(inverted[0])
                painter.setBrush(brush)
#            painter.drawEllipse(QRectF(position[0] + 0.1, position[1] + 0.1, 0.8, 0.8))

    return pixmap
