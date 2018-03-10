
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QRectF

def generate_wall(maze, QWidget):
    pixmap = QtGui.QPixmap(QWidget.width() * 2, QWidget.height() * 2)
    pixmap.fill(QtCore.Qt.transparent)
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
            painter.drawEllipse(QRectF(position[0] + 0.1, position[1] + 0.1, 0.8, 0.8))

    return pixmap
