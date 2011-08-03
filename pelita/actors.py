from pelita.messaging import Actor, DispatchingActor, expose, actor_registry, actor_of

from pelita.game_master import GameMaster
from pelita.player import AbstractPlayer
from pelita.viewer import AsciiViewer

import logging

_logger = logging.getLogger("pelita")
_logger.setLevel(logging.DEBUG)

class _ClientActor(DispatchingActor):
    def on_start(self):
        self.players = []

    @expose
    def add_player(self, message, player):
        self.players.append(player)

    @expose
    def say_hello(self, message, main_actor, team_name, host, port):
        self.server_actor = actor_registry.get_by_name(main_actor)
        if not self.server_actor:
            _logger.warning("Actor %r not found." % main_actor)
            return

        if self.server_actor.query("hello", [team_name, self.ref.uuid]).get() == "ok":
            _logger.info("Connection accepted")
            self.ref.reply("ok")

    @expose
    def set_index(self, message, index):
        self.ref.reply(self.players[0]._set_index(index))

    @expose
    def set_initial(self, message, universe):
        self.ref.reply(self.players[0]._set_initial(universe))

    @expose
    def play_now(self, message, universe):        
        self.ref.reply(self.players[0]._get_move(universe))


class ClientActor(object):
    def __init__(self, team_name):
        self.team_name = team_name

        self.server_actor = None
        self.actor_ref = actor_of(_ClientActor)
        self.actor_ref._actor.thread.daemon = True # TODO remove this line
        self.actor_ref.start()

    def register_player(self, player):
        self.actor_ref.notify("add_player", [player])

    def connect(self, main_actor, host="", port=50007):
        print self.actor_ref.query("say_hello", [main_actor, self.team_name, host, port]).get()




class RemotePlayer(AbstractPlayer):
    def __init__(self, reference):
        self.ref = reference

    def _set_index(self, index):
        return self.ref.query("set_index", [index])

    def _set_initial(self, universe):
        return self.ref.query("set_initial", [universe]).get(3)
    
    def get_move(self):
        pass

    def _get_move(self, universe):
        result = self.ref.query("play_now", [universe]).get(3)
        return result

class ServerActor(DispatchingActor):
    def on_start(self):
        self.teams = {}
        self.game_master = None

    @expose
    def initialize_game(self, message, layout, number_bots, game_time):
        self.game_master = GameMaster(layout, number_bots, game_time)

    @expose
    def hello(self, message, team_name, actor_uuid):
        _logger.info("Received 'hello' from '%s'." % team_name)

        if self.ref.remote:
            other_ref = self.ref.remote.create_proxy(actor_uuid)
        else:
            other_ref = actor_registry.get_by_uuid(actor_uuid)

        self.teams[team_name] = other_ref
        self.ref.reply("ok")

        if len(self.teams) == 2:
            _logger.info("Two players are available. Starting a game.")

            self.ref.notify("start_game")

    @expose
    def start_game(self, message):
        for team_name, actor_ref in self.teams.iteritems():
            print team_name, actor_ref
            
            self.game_master.register_player(RemotePlayer(actor_ref))

        self.game_master.register_viewer(AsciiViewer())
        self.game_master.play()

        self.ref.stop()

