""" The observers. """

import abc
import json
import sys

import zmq

class AbstractViewer(metaclass=abc.ABCMeta):
    def set_initial(self, universe):
        """ This method is called when the first universe is ready.
        """
        pass

    @abc.abstractmethod
    def observe(self, universe, game_state):
        pass

class ProgressViewer(AbstractViewer):
    def observe(self, universe, game_state):
        round_index = game_state["round_index"]
        game_time = game_state["game_time"]
        percentage = int(100.0 * round_index / game_time)
        if game_state["bot_id"] is not None:
            bot_sign = game_state["bot_id"]
        else:
            bot_sign = ' '
        string = ("[%s] %3i%% (%i / %i) [%s]" % (
                    bot_sign, percentage,
                    round_index, game_time,
                    ":".join(str(t.score) for t in universe.teams)))
        sys.stdout.write(string + ("\b" * len(string)))
        sys.stdout.flush()

        if game_state["finished"]:
            sys.stdout.write("\n")
            print("Final state:", game_state)

class AsciiViewer(AbstractViewer):
    """ A viewer that dumps ASCII charts on stdout. """

    def observe(self, universe, game_state):
        info = (
            "Round: {round!r} Turn: {turn!r} Score {s0}:{s1}\n"
            "Game State: {game_state!r}\n"
            "\n"
            "{universe}"
        ).format(round=game_state["round_index"],
                 turn=game_state["bot_id"],
                 s0=universe.teams[0].score,
                 s1=universe.teams[1].score,
                 game_state=game_state,
                 universe=universe.compact_str)

        print(info)
        winning_team_idx = game_state.get("team_wins")
        if winning_team_idx is not None:
            print(("Game Over: Team: '%s' wins!" %
                game_state["team_name"][winning_team_idx]))


class ReplyToViewer(AbstractViewer):
    """ A viewer which dumps to a given stream.
    """
    def __init__(self, reply_to):
        ctx = zmq.Context()
        self.sock = ctx.socket(zmq.PAIR)

        # Wait max linger ms for a socket to connect
        # before giving up.
        self.sock.linger = 1000

        self.sock.connect(reply_to)

        self.pollout = zmq.Poller()
        self.pollout.register(self.sock, zmq.POLLOUT)

    def _send(self, message):
        socks = dict(self.pollout.poll(300))
        if socks.get(self.sock) == zmq.POLLOUT:
            as_json = json.dumps(message)
            self.sock.send_unicode(as_json, flags=zmq.NOBLOCK)

    def set_initial(self, universe):
        message = {"__action__": "set_initial",
                   "__data__": {"universe": universe._to_json_dict()}}
        self._send(message)

    def observe(self, universe, game_state):
        message = {"__action__": "observe",
                   "__data__": {"universe": universe._to_json_dict(),
                                "game_state": game_state}}
        self._send(message)


class DumpingViewer(AbstractViewer):
    """ A viewer which dumps to a given stream.
    """
    def __init__(self, stream):
        self.stream = stream

    def _send(self, message):
        as_json = json.dumps(message)
        self.stream.write(as_json)
        self.stream.write("\x04")

    def set_initial(self, universe):
        message = {"__action__": "set_initial",
                   "__data__": {"universe": universe._to_json_dict()}}
        self._send(message)

    def observe(self, universe, game_state):
        message = {"__action__": "observe",
                   "__data__": {"universe": universe._to_json_dict(),
                                "game_state": game_state}}
        self._send(message)

