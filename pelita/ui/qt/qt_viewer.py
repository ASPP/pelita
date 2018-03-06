import cmath
import json
import logging
import math
import os
import shutil
import signal
import sys

import zmq

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QWidget, QApplication, QMainWindow
from PyQt5.QtCore import QPointF, QRectF

from pelita.graph import diff_pos
from pelita.datamodel import CTFUniverse

_logger = logging.getLogger(__name__)
_logger.setLevel(logging.DEBUG)

signal.signal(signal.SIGINT, signal.SIG_DFL)

class ZMQListener(QtCore.QThread):
    message = QtCore.pyqtSignal(str)

    def __init__(self, address, exit_address):
        super().__init__()
        self.address = address
        self.exit_address = exit_address
        self.running = True
    
    def run(self):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.setsockopt_unicode(zmq.SUBSCRIBE, "")
        self.socket.connect(self.address)

        self.exit_socket = self.context.socket(zmq.PAIR)
        self.exit_socket.connect(self.exit_address)

        self.poll = zmq.Poller()
        self.poll.register(self.socket, zmq.POLLIN)
        self.poll.register(self.exit_socket, zmq.POLLIN)

        while self.running:
            evts = dict(self.poll.poll(1000))
            if self.socket in evts:
                message = self.socket.recv_unicode()
                self.message.emit(message)
            if self.exit_socket in evts:
                self.running = False
 

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.resize(500, 500)
        self.centralwidget = QWidget(MainWindow)
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.centralwidget)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 500, 22))
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        MainWindow.setStatusBar(self.statusbar)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)


class QtViewer(QMainWindow):
    def __init__(self, address, controller_address=None, geometry=None, delay=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.context = zmq.Context()
        self.exit_socket = self.context.socket(zmq.PAIR)
        exit_address = self.exit_socket.bind_to_random_port('tcp://127.0.0.1')

        self.zmq_listener = ZMQListener(address, f'tcp://127.0.0.1:{exit_address}')
        self.zmq_listener.message.connect(self.signal_received)
        
        QtCore.QTimer.singleShot(0, self.zmq_listener.start)

        if controller_address:
            self.controller_socket = self.context.socket(zmq.DEALER)
            self.controller_socket.connect(controller_address)
        else:
            self.controller_socket = None

        if self.controller_socket:
            QtCore.QTimer.singleShot(0, self.request_initial)

        self.setupUi()

        self.ui = Ui_MainWindow()  # This is from a python export from QtDesigner
        self.ui.setupUi(self)

        self.running = True
        
        pause = QtWidgets.QShortcut(" ", self)
        pause.activated.connect(self.pause)

        self.universe = None
        self.food = []
        self.previous_positions = {}
        self.directions = {}


    @QtCore.pyqtSlot()
    def pause(self):
        self.running = not self.running
        self.request_next()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        width = self.width()
        height = self.height()
        pen_size = 0.05

        if self.universe:
            universe_width = self.universe.maze.width
            universe_height = self.universe.maze.height
            painter.scale(width / universe_width, height / universe_height)
            painter.setPen(QtGui.QPen(QtCore.Qt.black, pen_size))

            for food in self.food:
                painter.setPen(QtGui.QPen(QtCore.Qt.black, pen_size))
                painter.setBrush(QtGui.QColor(247, 150, 213))
                painter.drawEllipse(QRectF(food[0] + 0.3, food[1] + 0.3, 0.4, 0.4))

            for position, wall in self.universe.maze.items():
                if wall:
                    painter.setBrush(QtGui.QBrush())
                    painter.drawEllipse(QRectF(position[0] + 0.1, position[1] + 0.1, 0.8, 0.8))

            blue_col = QtGui.QColor(94, 158, 217)
            red_col = QtGui.QColor(235, 90, 90)
        
            for bot in self.universe.bots:
                def paint(pos):
                    painter.drawArc(QRectF(pos[0] + 0.2, pos[1] + 0.2, 0.6, 0.6), 0, 5760)

                def paint_harvester(pos, color):
                    direction = self.directions.get(bot.index)
                    if not direction:
                        direction = (0, 1)

                    rotation = math.degrees(cmath.phase(direction[0] - direction[1]*1j))

                    x, y = pos
                    bounding_rect = QRectF(x, y, 1, 1)
                    # bot body
                    path = QtGui.QPainterPath(QPointF(x + 0.5, y + 0.5))
                    path.arcTo(bounding_rect, 20 + rotation, 320)
                    path.closeSubpath()
                    painter.setBrush(color)

                    painter.drawPath(path)

                    painter.setBrush(QtGui.QColor(235, 235, 30))
                    eye_size = 0.1
                    # left eye
                    painter.drawEllipse(QRectF(x + 0.3 - eye_size, y + 0.3 - eye_size, eye_size * 2, eye_size * 2))

                def paint_destroyer(pos, color):
                    x, y = pos
                    bounding_rect = QRectF(x, y, 1, 1)
                    # ghost head
                    path = QtGui.QPainterPath(QPointF(x, y + 0.5))
                    path.lineTo(QPointF(x, y + 7/8))
                    path.cubicTo(QPointF(x + 0.5/6, y + 7/8), QPointF(x + 1/6, y + 7/8), QPointF(x + 1/6, y + 1/2))
                    path.cubicTo(QPointF(x + 1/6, y + 1), QPointF(x + 3/6, y + 1), QPointF(x + 3/6, y + 1/2))
                    path.cubicTo(QPointF(x + 3/6, y + 1), QPointF(x + 5/6, y + 1), QPointF(x + 5/6, y + 1/2))
                    path.cubicTo(QPointF(x + 5/6, y + 7/8), QPointF(x + 5.5/6, y + 7/8), QPointF(x + 6/6, y + 7/8))
                    path.lineTo(QPointF(x + 1, y + 0.5))
                    path.cubicTo(QPointF(x + 1, y), QPointF(x, y), QPointF(x, y+0.5))
                    painter.setBrush(color)

                    painter.drawPath(path)

                    # ghost eyes
                    eye_size = 0.15
                    painter.setBrush(QtGui.QColor(235, 235, 30))
                    # left eye
                    painter.drawEllipse(QRectF(x + 0.3 - eye_size, y + 0.3 - eye_size, eye_size * 2, eye_size * 2))
                    # right eye
                    painter.drawEllipse(QRectF(x + 0.7 - eye_size, y + 0.3 - eye_size, eye_size * 2, eye_size * 2))

                if bot.team_index == 0:
                    bot_col = blue_col
                else:
                    bot_col = red_col

                painter.setPen(QtGui.QPen(bot_col, pen_size))
                if bot.is_destroyer:
                    paint_destroyer(bot.current_pos, bot_col)
                else:
                    paint_harvester(bot.current_pos, bot_col)

    def setupUi(self):
        self.setObjectName("MainWindow")
        self.resize(277, 244)
        self.statusbar = QtWidgets.QStatusBar()
        self.statusbar.setObjectName("statusbar")
        self.setStatusBar(self.statusbar)

    def request_initial(self):
        if self.controller_socket:
            self.controller_socket.send_json({"__action__": "set_initial"})

    def request_next(self):
        if self.running:
            self.request_step()

    def request_step(self):
        if self.controller_socket:
            self.controller_socket.send_json({"__action__": "play_step"})

    def signal_received(self, message):
        message = json.loads(message)
        observed = message["__data__"]
        if observed:
            self.observe(observed)

    def observe(self, observed):
        universe = observed.get("universe")
        universe = CTFUniverse._from_json_dict(universe) if universe else None
        game_state = observed.get("game_state")

        if universe:
            self.food = universe.food
            self.universe = universe
            self.statusBar().showMessage(str([b.current_pos for b in universe.bots]))

            for bot in universe.bots:
                previous_pos = self.previous_positions.get(bot.index)
                if previous_pos:
                    diff = diff_pos(previous_pos, bot.current_pos)
                    if abs(diff[0]) + abs(diff[1]) == 1:
                        self.directions[bot.index] = diff

                self.previous_positions[bot.index] = bot.current_pos

            self.repaint()

            if self.running:
                QtCore.QTimer.singleShot(0, self.request_next)

    def closeEvent(self, event):
        self.exit_socket.send(b'')
        if self.controller_socket:
            self.controller_socket.send_json({"__action__": "exit"})
        #self.zmq_listener.wait(2000)
        event.accept()

