# -*- coding: utf-8 -*-

import tornado.websocket
import tornado.httpserver
import tornado.ioloop
import tornado.netutil
import tornado.web

import socket

import zmq
from zmq.eventloop.zmqstream import ZMQStream

import os

import json
import pelita

class ZMQPubSub:
    def __init__(self, callback):
        self.callback = callback

    def connect(self, path):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.connect(path)
        self.stream = ZMQStream(self.socket)
        self.stream.on_recv(self.callback)

    def subscribe(self, channel_id):
        self.socket.setsockopt_string(zmq.SUBSCRIBE, "")

class Application(tornado.web.Application):
    def __init__(self):
        self.path = 'ipc:///tmp/pelita.%i' % id(self)
        handlers = [
            (r"/static/(.*)", tornado.web.StaticFileHandler, {'path': os.path.join(os.path.dirname(__file__), '_static')}),
            (r"/ws-echo", EchoWebSocket, {'path': self.path})
        ]
        tornado.web.Application.__init__(self, handlers, debug=True)

class EchoWebSocket(tornado.websocket.WebSocketHandler):
    def initialize(self, path):
        self.path = path
        self._walls = None

    def check_origin(self, origin):
        return True

    def open(self):
        self.pubsub = ZMQPubSub(self.on_data)
        self.pubsub.connect(self.path)
        self.pubsub.subscribe("")

        print("WebSocket opened")

    def on_message(self, message):
        pass

    def on_close(self):
        print("WebSocket closed")

    def on_data(self, data):
        py_obj = json.loads(data[0].decode())
        data = py_obj.get("__data__") or {}

        universe = data.get("universe")
        universe = pelita.datamodel.CTFUniverse._from_json_dict(universe)
        game_state = data.get("game_state")
        if universe:

            self._walls = []
            for y in range(universe.maze.height):
                for x in range(universe.maze.width):
                    if universe.maze[x, y]:
                        self._walls.append("#")
                    else:
                        self._walls.append(" ")

            self._walls = "".join(self._walls)

            width = universe.maze.width
            height = universe.maze.height

            bots = []
            for bot in universe.bots:
                bot_data = bot.current_pos
                bots.append(bot_data)

            if game_state:
                teams = [{"name": game_state["team_name"][idx], "score": t.score}
                          for idx, t in enumerate(universe.teams)]
            else:
                teams = []

            data = {'walls': self._walls,
                    'width': width,
                    'height': height,
                    'bots': bots,
                    'food': [list(f) for f in universe.food],
                    'teams': teams,
                    'state': game_state
                    }
            data_json = json.dumps(data)
            self.write_message(data_json)

def init_app():
    application = Application()
    sockets = tornado.netutil.bind_sockets(0, '', family=socket.AF_INET)
    server = tornado.httpserver.HTTPServer(application)
    server.add_sockets(sockets)

    for s in sockets:
        print('Listening on %s, port %d' % s.getsockname()[:2])

    return application, sockets
