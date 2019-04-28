""" The observers. """

import abc
import json
import sys

import zmq

from . import datamodel

class AbstractViewer(metaclass=abc.ABCMeta):
    def set_initial(self, game_state):
        """ This method is called when the first universe is ready.
        """
        pass

    @abc.abstractmethod
    def observe(self, game_state):
        pass

class ProgressViewer(AbstractViewer):
    def show_state(self, game_state):
        return self.observe(game_state)

    def observe(self, game_state):
        score = game_state["score"]
        round_index = game_state["round"]
        if round_index is None:
            return
        game_time = game_state["max_rounds"]
        percentage = int(100.0 * round_index / game_time)
        if game_state["turn"] is not None:
            if game_state["turn"] % 2 == 0:
                bot_sign = f'\033[94m{game_state["turn"]}\033[0m'
            elif game_state["turn"] % 2 == 1:
                bot_sign = f'\033[91m{game_state["turn"]}\033[0m'
        else:
            bot_sign = ' '
        string = ("[%s] %3i%% (%i / %i) [%s]" % (
                    bot_sign, percentage,
                    round_index, game_time,
                    ":".join(str(s) for s in score)))
        sys.stdout.write(string + ("\b" * len(string)))
        sys.stdout.flush()

        if game_state["gameover"]:
            state = {}
            state.update(game_state)
            del state['walls']
            del state['food']

            sys.stdout.write("\n")
            print("Final state:", state)

class AsciiViewer(AbstractViewer):
    """ A viewer that dumps ASCII charts on stdout. """

    def observe(self, game_state):
        universe = datamodel.CTFUniverse._from_json_dict(game_state)

        state = {}
        state.update(game_state)
        del state['maze']
        del state['food']
        del state['teams']
        del state['bots']

        info = (
            "Round: {round!r} Turn: {turn!r} Score {s0}:{s1}\n"
            "Game State: {state!r}\n"
            "\n"
            "{universe}"
        ).format(round=game_state["round_index"],
                 turn=game_state["bot_id"],
                 s0=universe.teams[0].score,
                 s1=universe.teams[1].score,
                 state=state,
                 universe=universe.compact_str)

        print(info)
        winning_team_idx = state.get("team_wins")
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

    def set_initial(self, game_state):
        message = {"__action__": "set_initial",
                   "__data__": {"game_state": game_state}}
        self._send(message)

    def observe(self, game_state):
        message = {"__action__": "observe",
                   "__data__": {"game_state": game_state}}
        self._send(message)


class DumpingViewer(AbstractViewer):
    """ A viewer which dumps to a given stream.
    """
    def __init__(self, stream):
        self.stream = stream

    def _send(self, message):
        as_json = json.dumps(message)
        self.stream.write(as_json)
        # We use 0x04 (EOT) as a separator between the events.
        # The additional newline is for improved readability
        # and should be ignored by the Python json reader.
        self.stream.write("\x04\n")
        self.stream.flush()

    def set_initial(self, game_state):
        message = {"__action__": "set_initial",
                   "__data__": {"game_state": game_state}}
        self._send(message)

    def observe(self, game_state):
        message = {"__action__": "observe",
                   "__data__": {"game_state": game_state}}
        self._send(message)

