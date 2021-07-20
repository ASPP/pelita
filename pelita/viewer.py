""" The observers. """

import json
import logging

import zmq

from . import layout
from .network import SetEncoder

_logger = logging.getLogger(__name__)



class ProgressViewer:
    def show_state(self, game_state):
        score = game_state["score"]
        round_index = game_state["round"]
        if round_index is None:
            return
        game_time = game_state["max_rounds"]
        percentage = int(100.0 * round_index / game_time)
        turn = game_state["turn"]
        if turn is not None:
            bot_idx = turn // 2
            if turn % 2 == 0:
                bot_sign = f'\033[94mBlue Team, Bot {bot_idx}\033[0m'
            elif turn % 2 == 1:
                bot_sign = f'\033[91mRed Team, Bot {bot_idx}\033[0m'
        else:
            bot_sign = ' '
        string = ("[%s] %3i%% (%i / %i) [%s]" % (
                    bot_sign, percentage,
                    round_index, game_time,
                    ":".join(str(s) for s in score)))
        print(string + ("\b" * len(string)), flush=True)

        if game_state["gameover"]:
            state = {}
            state.update(game_state)
            del state['walls']
            del state['food']

            print()
            print("Final state:", state)

class AsciiViewer:
    """ A viewer that dumps ASCII charts on stdout. """

    def color_bots(self, layout_str):
        out_str = layout_str
        for turn, char in layout.BOT_I2N.items():
            team = turn % 2
            col = '\033[94m' if team == 0 else '\033[91m'
            out_str = out_str.replace(char, f'{col}{char}\033[0m')

        return out_str

    def show_state(self, game_state):
        uni_str = layout.layout_as_str(walls=game_state['walls'],
                                       food=game_state['food'],
                                       bots=game_state['bots'])

        # color bots
        uni_str = self.color_bots(uni_str)
        # Everything that we print explicitly is removed from the state dict.
        state = {}
        state.update(game_state)
        # for death and kills just leave a summary
        state['blue deaths'] = state['deaths'][::2]
        state['blue kills'] = state['kills'][::2]
        state['red deaths'] = state['deaths'][1::2]
        state['red kills'] = state['kills'][1::2]
        del state['kills']
        del state['deaths']
        del state['walls']
        del state['food']
        del state['bots']
        del state['round']
        del state['turn']
        del state['score']

        turn = game_state["turn"]
        if turn is not None:
            team = 'Blue' if turn % 2 == 0 else 'Red'
            bot_idx = turn // 2
            bot_name = layout.BOT_I2N[bot_idx]
        else:
            team = '–'
            bot_name = '–'
        round=game_state["round"]
        s0=game_state["score"][0]
        s1=game_state["score"][1]
        state=state
        universe=uni_str
        length = len(universe.splitlines()[0])
        info = (
                f"Round: {round!r} | Team: {team} | Bot: {bot_name} | Score {s0}:{s1}\n"
            f"Game State: {state!r}\n"
            f"\n"
            f"{universe}\n")

        print(info+"–"*length)
        if state.get("gameover"):
            if state["whowins"] == 2:
                print("Game Over: Draw.")
            else:
                winner = game_state["team_names"][state["whowins"]]
                print(f"Game Over: Team: '{winner}' wins!")


class ReplyToViewer:
    """ A viewer which dumps to a given stream.
    """
    def __init__(self, reply_to):
        ctx = zmq.Context()
        self.sock = ctx.socket(zmq.PAIR)

        # Wait max linger ms for a socket to connect
        # before giving up.
        self.sock.linger = 1000

        self.sock.connect(reply_to)
        _logger.debug(f"Connecting zmq.PAIR to {reply_to}")

        self.pollout = zmq.Poller()
        self.pollout.register(self.sock, zmq.POLLOUT)

    def _send(self, message):
        socks = dict(self.pollout.poll(300))
        if socks.get(self.sock) == zmq.POLLOUT:
            as_json = json.dumps(message, cls=SetEncoder)
            self.sock.send_unicode(as_json, flags=zmq.NOBLOCK)

    def show_state(self, game_state):
        self._send(game_state)


class ReplayWriter:
    """ A viewer which dumps to a given stream.
    """
    def __init__(self, stream):
        self.stream = stream

    def _send(self, message):
        as_json = json.dumps(message, cls=SetEncoder)
        self.stream.write(as_json)
        # We use 0x04 (EOT) as a separator between the events.
        # The additional newline is for improved readability
        # and should be ignored by the Python json reader.
        self.stream.write("\x04\n")
        self.stream.flush()

    def show_state(self, game_state):
        self._send(game_state)


class ResultPrinter:
    def show_state(self, state):
        if state["gameover"]:
            self.print_possible_winner(state)

    def print_possible_winner(self, state):
        """ Checks the game state for a winner.

        This is needed for pelita.scripts parsing the output.
        """
        winning_team = state.get("whowins")
        if state['round'] == 1:
            num_rounds = "1 round"
        else:
            num_rounds = f"{state['round']} rounds"
        if winning_team in (0, 1):
            winner = state['team_names'][winning_team]
            loser = state['team_names'][1 - winning_team]
            winner_score = state['score'][winning_team]
            loser_score = state['score'][1 - winning_team]
            msg = f"Finished after {num_rounds}. '{winner}' won over '{loser}'. ({winner_score}:{loser_score})"
        elif winning_team == 2:
            t1, t2 = state['team_names']
            s1, s2 = state['score']
            msg = f"Finished after {num_rounds}. '{t1}' and '{t2}' had a draw. ({s1}:{s2})"
        else:
            return

        # We must flush, else our forceful stopping of Tk
        # won't let us pipe it.
        print(msg, flush=True)
