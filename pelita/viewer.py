""" The observers. """

import json
import logging
import sys

import zmq
from rich.console import Console
from rich.progress import (BarColumn, MofNCompleteColumn, Progress,
                           SpinnerColumn, TextColumn, TimeElapsedColumn)

from . import layout
from .network import SetEncoder

_logger = logging.getLogger(__name__)
_mswindows = (sys.platform == "win32")

# Only highlight explicit markup
pprint = Console(highlight=False).print

class ProgressViewer:
    def __init__(self) -> None:
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
        )
        self.task = self.progress.add_task('[Pelita]', total=None)

    def show_state(self, game_state):
        score = game_state["score"]
        round_index = game_state["round"]
        if round_index is None:
            return
        game_time = game_state["max_rounds"]

        turn = game_state["turn"]
        if turn is not None:
            bot_idx = turn // 2
            if turn % 2 == 0:
                bot_sign = f'[blue]Blue Team, Bot {bot_idx}[/]'
            elif turn % 2 == 1:
                bot_sign = f'[red]Red Team,  Bot {bot_idx}[/]'
        else:
            bot_sign = ' '

        score = ":".join(str(s) for s in score)
        status = f"[{bot_sign}] [{score}]"

        self.progress.update(self.task, description=status, total=game_time,
                             completed=round_index, refresh=True)
        self.progress.start()

        if game_state["gameover"]:
            state = {}
            state.update(game_state)
            del state['walls']
            del state['food']

            self.progress.stop()
            self.progress.console.clear_live()

            print()
            print(f"Final state: {state}")


class AsciiViewer:
    """ A viewer that dumps ASCII charts on stdout. """

    def color_bots(self, layout_str):
        out_str = layout_str
        # we have to do the replace in two steps to avoid
        # that the ‘b’ in ‘[blue]’ gets replaced with itself
        for turn, char in layout.BOT_I2N.items():
            team = turn % 2
            col = '[B]' if team == 0 else '[R]'
            out_str = out_str.replace(char, f'{col}{char}[/]')

        out_str = out_str.replace('B', 'blue').replace('R', 'red')

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
        )

        print(info)
        pprint(universe)
        print("–"*length)
        if state.get("gameover"):
            if state["whowins"] == 2:
                pprint("Game Over: Draw.")
            else:
                winner = game_state["team_names"][state["whowins"]]
                pprint(f"Game Over: Team: '{winner}' wins!")


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
        if (state['turn'] is None and
            state['round'] is None):
            # TODO: We must ensure that this is only printed once
            self.print_team_names(state['team_names'])

        if state["gameover"]:
            self.print_possible_winner(state)

    def print_team_names(self, team_names):
        # TODO: The team_spec is missing in the state.
        # Should we print it here?
        pie = '' if _mswindows else 'ᗧ'

        for col, team_name in zip(['blue', 'red'], team_names):
            if team_name is not None:
                pprint(f"[bright_{col}]{pie}[/bright_{col}] {col} team: '{team_name}'")

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
