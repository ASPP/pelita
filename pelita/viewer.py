""" The observers. """

import json
import logging
import sys
import time

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

    def show_state(self, game_state):
        G = game_state

        # get the parts to printed on screen
        parts = [
            format_part(G) 
            for format_part in (
                self.format_header, self.format_maze, self.format_footer
            )
        ]
        screen = "\n".join(parts)

        if G["round"] is None:
            # the cursor might be somewhere in the terminal screen
            # alongside some content
            self.clear_screen()

        # print in one go to avoid screen flicker
        pprint(screen)

        # give the user time to recognize the content
        time.sleep(0.2)

        if not G.get("gameover"):
            # clear for new content to achieve an update effect;
            # relies on consistent formatting
            self.clear_screen()

    def clear_screen(self):
        """
        Clear the terminal screen.

        This method uses ANSI control sequences.
        See https://en.wikipedia.org/wiki/ANSI_escape_code#Control_Sequence_Introducer_commands for more detail
        """
        # \033 starts an ANSI escape code
        # \033[ inits a Control Sequence Introducer command
        # \033[H brings the cursor the default position 1, 1
        # \033[2J erases the entire screen
        print("\033[H\033[2J", end="")

    def format_header(self, game_state):
        """
        Create the header from the game state.
        """
        G = game_state
        lines = []

        # format the rounds counter
        rounds = G["round"] or "-"
        max_rounds = G["max_rounds"]
        length = len(str(max_rounds))
        template = f"R {{rounds: >{length}}}/{max_rounds}"

        lines.append(template.format(rounds=rounds))

        # separate counter from team stats
        lines.append("")

        # prepare arguments for team stats
        turn = G["turn"]
        turns = [False] * 4
        if turn is not None:
            turns[turn] = True

        turns = ((turns[0], turns[2]), (turns[1], turns[3]))

        # append team stats
        for args in zip(
            G["score"],
            [["a", "b"], ["x", "y"]],
            turns,
            G["team_names"],
            ("blue", "red"),
        ):
            lines.append(self.format_team_stats(*args))

        # separate header from following parts
        lines.append("")

        return "\n".join(lines)

    def format_team_stats(self, score, bots, turns, name, color):
        """
        Arrange stats for a team.
        """
        # color all bots;
        # mark the currently moving bot
        for i, bot in enumerate(bots.copy()):
            bot = self.color(bot, color)
            if turns[i]:
                bots[i] = f"({bot})"
            else:
                bots[i] = f" {bot} "

        # color pacman symbol and team name
        pie = self.color("ᗧ", color)
        name = self.color(name, color)
            
        return f"{pie} {score:4d} {bots[0]} {bots[1]} {name}"

    def format_maze(self, game_state):
        """
        Create the maze from the game state.
        """
        G = game_state

        maze = layout.layout_as_str(
            walls=G["walls"], food=G["food"], bots=G["bots"]
        )

        # prepare bots and colors
        bots = layout.BOT_N2I.keys()
        colors = ["blue"] * 2 + ["red"] * 2
        bots_and_colors = tuple(zip(bots, colors))

        # choose a temporary bot name not included in the color
        # formatting itself, like bot `b`
        template = "_{}_"

        # replace bot names with temporary ones
        for bot, color in bots_and_colors:
            tmp_bot = template.format(bot)
            maze = maze.replace(bot, tmp_bot)

        # replace temporary bot names with colored names
        for bot, color in bots_and_colors:
            tmp_bot = template.format(bot)
            new_bot = self.color(bot, color)
            maze = maze.replace(tmp_bot, new_bot)

        # replace ASCII with block characters
        maze = maze.replace("#", "\N{FULL BLOCK}")

        return maze

    def format_footer(self, game_state):
        """
        Create the footer from the game state.

        If bots are saying a message, it shows up here.
        """
        G = game_state

        lines = []
        template = "{bot}: '{msg}'"

        # prepare bots and colors
        bots = layout.BOT_N2I.keys()
        colors = ["blue"] * 2 + ["red"] * 2

        # color a non-empty bot message
        for color, bot, msg in zip(colors, bots, G["say"]):
            if msg:
                bot_line = template.format(bot=bot, msg=msg)
                bot_line = self.color(bot_line, color)
                lines.append(bot_line)

        # only separate from following parts if there is any content
        if lines:
            lines.append("")

        return "\n".join(lines)

    def color(self, out, color):
        """
        Color a given string.
        """
        return f"[{color}]{out}[/]"




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
