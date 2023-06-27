
import json
import logging
import signal
from pathlib import Path

import zmq
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import (QCoreApplication, QObject, QPointF, QRectF,
                          QSocketNotifier, pyqtSignal, pyqtSlot)
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (QApplication, QGraphicsView, QGridLayout,
                             QHBoxLayout, QVBoxLayout, QMainWindow, QPushButton, QWidget)

from ...game import next_round_turn
from .qt_items import EndTextOverlay
from .qt_scene import PelitaScene, blue_col, red_col

_logger = logging.getLogger(__name__)
_logger.setLevel(logging.DEBUG)

signal.signal(signal.SIGINT, signal.SIG_DFL)



class ZMQListener(QObject):
    signal_received = pyqtSignal(str)

    def __init__(self, address, exit_address):
        super().__init__()
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.connect(address)
        self.socket.subscribe(b"")

        self.exit_socket = self.context.socket(zmq.PAIR)
        self.exit_socket.connect(exit_address)

        # TODO: Not sure if this is working on Windows
        self.notifier = QSocketNotifier(self.socket.getsockopt(zmq.FD), QSocketNotifier.Type.Read, self)
        self.notifier.activated.connect(self.handle_signal)

    @pyqtSlot()
    def handle_signal(self):
        while self.socket.getsockopt(zmq.EVENTS) & zmq.POLLIN:
            message = self.socket.recv_unicode(zmq.NOBLOCK)
            self.signal_received.emit(message)


class QtViewer(QMainWindow):
    def __init__(self, address, controller_address=None,
                       geometry=None, delay=None, export=None, stop_after=None,
                       *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle("Pelita")

        if export:
            png_export_path = Path(export)
            if not png_export_path.is_dir():
                raise RuntimeError(f"Not a directory: {png_export_path}")
            self.png_export_path = png_export_path
        else:
            self.png_export_path = None

        nIOthreads = 2
        self.context = zmq.Context(nIOthreads)
        self.exit_socket = self.context.socket(zmq.PAIR)
        self.exit_socket.setsockopt(zmq.LINGER, 0)
        self.exit_socket.setsockopt(zmq.AFFINITY, 1)
        self.exit_socket.setsockopt(zmq.RCVTIMEO, 2000)
        exit_address = self.exit_socket.bind_to_random_port('tcp://127.0.0.1')

        self.zmq_listener = ZMQListener(address, 'tcp://127.0.0.1:{}'.format(exit_address))
        self.zmq_listener.signal_received.connect(self.signal_received)

        #QtCore.QTimer.singleShot(0, self.zmq_listener.start)

        if controller_address:
            self.controller_socket = self.context.socket(zmq.DEALER)
            self.controller_socket.setsockopt(zmq.LINGER, 0)
            self.controller_socket.setsockopt(zmq.AFFINITY, 1)
            self.controller_socket.setsockopt(zmq.RCVTIMEO, 2000)
            self.controller_socket.connect(controller_address)
        else:
            self.controller_socket = None

        if self.controller_socket:
            QtCore.QTimer.singleShot(0, self.request_initial)

        self.setupUi()

        self.running = False
        self._observed_steps = set()

        self._min_delay = 1
        self._delay = delay
        self._stop_after = stop_after
        self._stop_after_delay = delay
        if self._stop_after is not None:
            self._delay = self._min_delay

        self.pause_button.clicked.connect(self.pause)
        self.button.clicked.connect(self.close)
        self.button.setShortcut("q")
        self.step_button.clicked.connect(self.request_step)
        self.step_button.setShortcut("Return")

        self.round_button.clicked.connect(self.request_round)
        self.round_button.setShortcut("Shift+Return")

        self.debug_button.clicked.connect(self.toggle_debug)
        self.debug_button.setShortcut("#")

        # .activated is faster than .clicked which makes sense here
        QShortcut(" ", self).activated.connect(self.pause_button.click)
        #QShortcut("q", self).activated.connect(self.button.click)
        #QShortcut(QKeySequence("Return"), self).activated.connect(self.request_step)
        #QShortcut(QKeySequence("Shift+Return"), self).activated.connect(self.request_round)


    @QtCore.pyqtSlot()
    def toggle_debug(self):
        self.scene.grid = not self.scene.grid
        self.scene.show_grid()
        self.view.resetCachedContent()
        self.view.update()

    @QtCore.pyqtSlot()
    def pause(self):
        self.running = not self.running
        self.request_next()

    def resizeEvent(self, event):
        if hasattr(self, 'wall_pm'):
            del self.wall_pm

    def setupUi(self):
        self.resize(900, 620)

        # Create a central widget and set the layout
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        grid_layout = QGridLayout(central_widget)

        blue_info = QWidget(self)
        blue_info_layout = QHBoxLayout(blue_info)
        blue_info_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        red_info = QWidget(self)
        red_info_layout = QHBoxLayout(red_info)
        red_info_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)

        self.team_blue = QtWidgets.QLabel("Score")
        self.team_blue.setStyleSheet(f"color: {blue_col.name()}; font-weight: bold;")
        self.team_red = QtWidgets.QLabel("Score")
        self.team_red.setStyleSheet(f"color: {red_col.name()}; font-weight: bold;")

        self.score_blue = QtWidgets.QLabel("0")
        self.score_red = QtWidgets.QLabel("0")

        blue_info_layout.addWidget(self.team_blue)
        blue_info_layout.addWidget(self.score_blue)

        red_info_layout.addWidget(self.score_red)
        red_info_layout.addWidget(self.team_red)


        self.stats_blue = QtWidgets.QLabel("Stats")
        self.stats_blue.setStyleSheet(f"color: {blue_col.name()};")
        self.stats_blue.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self.stats_red = QtWidgets.QLabel("Stats")
        self.stats_red.setStyleSheet(f"color: {red_col.name()};")
        self.stats_red.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)

        self.pause_button = QtWidgets.QPushButton("PLAY/PAUSE")
        self.step_button = QtWidgets.QPushButton("STEP")
        self.round_button = QtWidgets.QPushButton("ROUND")

        self.slower_button = QtWidgets.QPushButton("slower")
        self.faster_button = QtWidgets.QPushButton("faster")
        self.debug_button = QtWidgets.QPushButton("debug")

        self.button = QtWidgets.QPushButton("QUIT")

        self.scene = PelitaScene()
        #self.scene.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        #self.scene.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.view = GameView(self.scene)
        self.view.setCacheMode(QGraphicsView.CacheModeFlag.CacheBackground)

        game_layout_w = QWidget(self)
        game_layout = QVBoxLayout(game_layout_w)
        game_layout.addWidget(self.view)
        game_layout.addStretch()

        bottom_info = QWidget(self)
        bottom_info_layout = QHBoxLayout(bottom_info)

        bottom_info_layout.addWidget(self.pause_button)
        bottom_info_layout.addWidget(self.step_button)
        bottom_info_layout.addWidget(self.round_button)
        bottom_info_layout.addWidget(self.debug_button)

        grid_layout.addWidget(blue_info, 0, 0)
        grid_layout.addWidget(red_info, 0, 1)

        grid_layout.addWidget(self.stats_blue, 1, 0)
        grid_layout.addWidget(self.stats_red, 1, 1)

        grid_layout.addWidget(game_layout_w, 2, 0, 1, 2)
        grid_layout.addWidget(bottom_info, 3, 0, 1, 2)
        grid_layout.addWidget(self.button, 4, 0, 1, 2)


#        menubar = QtWidgets.QMenuBar(None)
#        self.setMenuBar(menubar)
#        self.statusbar = QtWidgets.QStatusBar(self)
#        self.setStatusBar(self.statusbar)

        QtCore.QMetaObject.connectSlotsByName(self)


    def request_initial(self):
        if self.controller_socket:
            try:
                self.controller_socket.send_json({"__action__": "set_initial"})
            except zmq.ZMQError:
                print("Socket already closed. Ignoring.")

            self.running = True

    def request_next(self):
        if self.running:
            self.request_step()

    def request_step(self):
        if not self.controller_socket:
            return

        if self._game_state['gameover']:
            return

        if self._stop_after is not None:
            next_step = next_round_turn(self._game_state)
            if (next_step['round'] < self._stop_after):
                _logger.debug('---> play_step')
                try:
                    self.controller_socket.send_json({"__action__": "play_step"})
                except zmq.ZMQError:
                    print("Socket already closed. Ignoring.")
            else:
                self._stop_after = None
                self.running = False
                self._delay = self._stop_after_delay
        else:
            _logger.debug('---> play_step')
            self.controller_socket.send_json({"__action__": "play_step"})

    def request_round(self):
        if not self.controller_socket:
            return

        if self._game_state['gameover']:
            return

        if self._game_state['round'] is not None:
            next_step = next_round_turn(self._game_state)
            self._stop_after = next_step['round'] + 1
        else:
            self._stop_after = 1
            self._delay = self._min_delay
        self.request_step()


    def signal_received(self, message):
        message = json.loads(message)
        observed = message["__data__"]
        if observed:
            self.observe(observed)

    def observe(self, game_state):
        step = (game_state['round'], game_state['turn'])
        if step in self._observed_steps:
            skip_request = True
        else:
            skip_request = False
            self._observed_steps.add(step)

        # We do this the first time we know what our shape is
        # fitInView invalidates the caching of the background
        if game_state['shape'] and not self.scene.shape:
            self.scene.shape = game_state['shape']
            w, h = self.scene.shape
            self.scene.setSceneRect(0, 0, w, h)
            self.view.fitInView(0, 0, w, h)

        self._game_state = game_state
        self.scene.game_state = game_state

        self.scene.walls = game_state['walls']
        self.scene.food = [tuple(food) for food in game_state['food']]
        self.scene.bots = game_state['bots']
        self.scene.requested_moves = game_state['requested_moves']

        self.scene.init_scene()

        for pos in self.scene.food_items.keys():
            if not pos in self.scene.food:
                self.scene.hide_food(pos)

        for idx, pos in enumerate(self.scene.bots):
            self.scene.move_bot(idx, pos)


        # for bot_id, bot_sprite in self.scene.shadow_bot_items.items():
        #     if self._grid_enabled:
        #         shadow_bots = game_state.get('noisy_positions')
        #     else:
        #         shadow_bots = None

        #     if shadow_bots is None or shadow_bots[bot_id] is None:
        #         bot_sprite.delete(self.ui.game_canvas)
        #     else:
        #         bot_sprite.move_to(shadow_bots[bot_id],
        #                             self.ui.game_canvas,
        #                             game_state,
        #                             force=self.size_changed,
        #                             show_id=self._grid_enabled)

        self.scene.update_arrow()

        self.team_blue.setText(f"{game_state['team_names'][0]}")
        self.team_red.setText(f"{game_state['team_names'][1]}")
        self.score_blue.setText(str(game_state['score'][0]))
        self.score_red.setText(str(game_state['score'][1]))


        def status(team_idx):
            try:
                # sum the deaths of both bots in this team
                deaths = game_state['deaths'][team_idx] + game_state['deaths'][team_idx+2]
                kills = game_state['kills'][team_idx] + game_state['kills'][team_idx+2]
                ret = "Errors: %d, Kills: %d, Deaths: %d, Time: %.2f" % (game_state["num_errors"][team_idx], kills, deaths, game_state["team_time"][team_idx])
                return ret
            except TypeError:
                return ""

        self.stats_blue.setText(status(0))
        self.stats_red.setText(status(1))

        if game_state['gameover']:
            winning_team_idx = game_state.get("whowins")
            if winning_team_idx is None:
                gameover = EndTextOverlay("GAME OVER")

            elif winning_team_idx in (0, 1):
                win_name = game_state["team_names"][winning_team_idx]

                # shorten the winning name
                plural = '' if win_name.endswith('s') else 's'
                if len(win_name) > 25:
                    win_name = win_name[:22] + '...'

                gameover = EndTextOverlay(f"GAME OVER\n{win_name} win{plural}!")

            elif winning_team_idx == 2:
                gameover = EndTextOverlay("GAME OVER\nDRAW!")

            gameover.setScale(0.5)

            self.scene.addItem(gameover)


        # TODO: Not sure if we want/need this here
        # Qt updates itself just fine once this method returns
        self.scene.update()


        if self.png_export_path:
            try:
                round_index = game_state['round']
                bot_id = game_state['turn']
                file_name = 'pelita-{}-{}.png'.format(round_index, bot_id)

                self.grab().save(str(self.png_export_path / file_name))
            except TypeError as e:
                print(e)

        if self._stop_after is not None:
            if self._stop_after == 0:
                self._stop_after = None
                self.running = False
                self._delay = self._stop_after_delay
            else:
                if skip_request:
                    _logger.debug("Skipping next request.")
                else:
                    QtCore.QTimer.singleShot(self._delay, self.request_step)
        elif self.running:
            if skip_request:
                _logger.debug("Skipping next request.")
            else:
                QtCore.QTimer.singleShot(self._delay, self.request_step)

    def closeEvent(self, event):
        self.exit_socket.send(b'')
        self.exit_socket.close()

        if self.controller_socket:
            try:
                self.controller_socket.send_json({"__action__": "exit"})
            except zmq.ZMQError:
                print("Socket already closed. Ignoring.")

            self.controller_socket.close()

        event.accept()

class GameView(QGraphicsView):
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)

    def minimumHeight(self) -> int:
        return super().minimumHeight()

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, a0: int) -> int:
        return a0 // 2

    def resizeEvent(self, event) -> None:
        if self.scene().shape:
            x, y = self.scene().shape
            self.fitInView(0, 0, x, y)
        return super().resizeEvent(event)

    def event(self, event: QtCore.QEvent) -> bool:
        # we monitor the switch to dark mode
        if (event.type() == QtCore.QEvent.Type.ApplicationPaletteChange or
            event.type() == QtCore.QEvent.Type.PaletteChange):
            self.resetCachedContent()
        return super().event(event)
