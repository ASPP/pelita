# -*- coding: utf-8 -*-

import tornado.websocket
import tornado.httpserver
import tornado.ioloop
import tornado.netutil
import tornado.web

import socket

import zmq
from zmq.eventloop.zmqstream import ZMQStream

from IPython.core.display import HTML
import os

from ..messaging.json_convert import json_converter
from ..datamodel import Wall, Food

import json

class WebWrapper:
    def __init__(self):
        pass

    def show(self):
        pass



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
            (r"/", HomePageHandler),
            (r"/static/(.*)", tornado.web.StaticFileHandler, {'path': os.path.join(os.path.dirname(__file__), '_static')}),
            (r"/ws-echo", EchoWebSocket, {'path': self.path})
        ]
        tornado.web.Application.__init__(self, handlers, debug=True)

# Handle the home page/index request.
# @route("/").
class HomePageHandler(tornado.web.RequestHandler):
    def get(self):
        #       self.render("index.html")
        self.render_string("index.html")
        self.write("hi")

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
        # self.write_message(u"You said: " + message)

    def on_close(self):
        print("WebSocket closed")

    def on_data(self, data):
        msg_objs = json_converter.loads(data[0].decode())

        data = msg_objs.get("__data__") or {}

        universe = data.get("universe")
        game_state = data.get("game_state")
        if universe:

            self._walls = []
            for y in range(universe.maze.height):
                for x in range(universe.maze.width):
                    if Wall in universe.maze[x, y]:
                        self._walls.append("#")
                    elif Food in universe.maze[x, y]:
                        self._walls.append(".")
                    else:
                        self._walls.append(" ")

            self._walls = "".join(self._walls)

            food = []
            for x in range(universe.maze.width):
                col = []
                for y in range(universe.maze.height):
                    col += [Food in universe.maze[x, y]]
                food.append(col)

            width = universe.maze.width
            height = universe.maze.height

            bots = []
            for bot in universe.bots:
                bot_data = bot.current_pos
                bots.append(bot_data)

            teams = [{"name": t.name, "score": t.score} for t in universe.teams]

            data = {'walls': self._walls,
                    'width': width,
                    'height': height,
                    'bots': bots,
                    'food': food,
                    'teams': teams,
                    'state': game_state
                    }
            data_json = json.dumps(data)
            # print data_json
            self.write_message(data_json)


IFRAME = """

"""

def printit():
    application = Application()
    sockets = tornado.netutil.bind_sockets(0, '', family=socket.AF_INET)
    server = tornado.httpserver.HTTPServer(application)
    server.add_sockets(sockets)

    for s in sockets:
        print('Listening on %s, port %d' % s.getsockname()[:2])

#    tornado.ioloop.IOLoop.current().start()
    return application, sockets
