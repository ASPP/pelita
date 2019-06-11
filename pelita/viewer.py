""" The observers. """

import json
import logging
from pathlib import Path

import zmq

from . import layout

_logger = logging.getLogger(__name__)

class ProgressViewer:
    def show_state(self, game_state):
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

    def show_state(self, game_state):
        uni_str = layout.layout_as_str(walls=game_state['walls'],
                                       food=game_state['food'],
                                       bots=game_state['bots'])

        # Everything that we print explicitly is removed from the state dict.
        state = {}
        state.update(game_state)
        del state['walls']
        del state['food']
        del state['bots']
        del state['round']
        del state['turn']
        del state['score']

        info = (
            "Round: {round!r} Turn: {turn!r} Score {s0}:{s1}\n"
            "Game State: {state!r}\n"
            "\n"
            "{universe}"
        ).format(round=game_state["round"],
                 turn=game_state["turn"],
                 s0=game_state["score"][0],
                 s1=game_state["score"][1],
                 state=state,
                 universe=uni_str)

        print(info)
        if state.get("gameover"):
            if state["whowins"] == 2:
                print("Game Over: Draw.")
            else:
                winner = game_state["team_names"][state["whowins"]]
                print(f"Game Over: Team: '{winner}' wins!")


class SVGViewer:
    def __init__(self, folder):
        _logger.info(f"Writing SVG to {folder}.")
        self.folder = Path(folder)
        self.folder.mkdir()
        self.index = 0
    def show_state(self, game_state):
        # svg scaled up by a factor of 12
        SCALE = 12

        # blue_col = rgb(94, 158, 217)
        # red_col = rgb(235, 90, 90)

        width, height = layout.wall_dimensions(game_state['walls'])

        wall_elems = []
        for x, y in game_state['walls']:
            x1 = x
            y1 = y
            neighbor_elems = [
                (x + dx, y + dy) for dx, dy in [(-1, 0), (1, 0), (0, 1), (0, -1)]
                if (x + dx, y + dy) in game_state['walls']
            ]
            if neighbor_elems:
                for x2, y2 in neighbor_elems:
                    wall_elems.append((x1 + 0.5, x2 + 0.5, y1 + 0.5, y2 + 0.5))
            else:
                wall_elems.append((x1 + 0.5, x1 + 0.5, y1 + 0.5, y1 + 0.5))


        border_paths = "\n".join(
            f"""<line x1="{x1 * SCALE}" x2="{x2 * SCALE}" y1="{y1 * SCALE}" y2="{y2 * SCALE}" />"""
            for x1, x2, y1, y2 in wall_elems
        )

        bots = []
        border = width // 2
        for idx, bot in enumerate(game_state['bots']):
            if idx % 2 == 0:
                col = "blue"
                bot_type = "ghost" if bot[0] < border else "pacman"
            else:
                col = "red"
                bot_type = "pacman" if bot[0] < border else "ghost"
            dx = bot[0] * SCALE
            dy = bot[1] * SCALE
            bot_def = f""" <use transform="translate({dx},{dy})" xlink:href="#{bot_type}" class="{col}" /> """
            bots.append(bot_def)
        bots = "\n".join(bots)

        food = "\n".join(
            f"""<circle cx="{x * SCALE + 6}" cy="{y * SCALE + 6}" r="3" class="{"foodblue" if x < border else "foodred"}"/> """
            for x, y in game_state['food']
        )

        template = f"""
        <svg width="{width * 12}"
                height="{height * 12}"
                xmlns="http://www.w3.org/2000/svg"
                xmlns:xlink="http://www.w3.org/1999/xlink"
        >
        <defs>
        <style type="text/css"><![CDATA[
        line {{
            stroke: #000000;
            stroke-linecap: round;
            stroke-width: 3;
        }}
        .foodblue {{
            stroke: rgb(94, 158, 217);
            fill: none;
        }}
        .foodred {{
            stroke: rgb(235, 90, 90);
            fill: none;
        }}
        .blue {{
            fill: rgb(94, 158, 217);
        }}
        .red {{
            fill: rgb(235, 90, 90);
        }}
        ]]></style>

        <g id="pacman">
        <path d="M 9.98
        7.73
        A 4.38 4.38 0 1 1 9.98 3.8
        L 6.05 5.8
        Z"
        />
        </g>

        <g id="ghost">
            <path d="M 2 6 
        C 2 3.79 3.8 2 6 2
        C 8.21 2 10 3.8 10 6
        L 10 10
        L 9.01 8.81
        L 8.01 10
        L 7 8.81
        L 6.01 10
        L 5.01 8.81
        L 4 10
        L 3 8.81
        L 2 10
        L 2 6
        Z
        M 4.39 6.54
        C 4.9 6.54 5.31 6.03 5.31 5.38
        C 5.31 4.74 4.9 4.22 4.39 4.22
        C 3.88 4.22 3.47 4.74 3.47 5.38
        C 3.47 6.03 3.88 6.54 4.39 6.54
        Z
        M 6.9 6.54
        C 7.41 6.54 7.82 6.03 7.82 5.38
        C 7.82 4.74 7.41 4.22 6.9 4.22
        C 6.39 4.22 5.98 4.74 5.98 5.38
        C 5.98 6.03 6.39 6.54 6.9 6.54
        Z
        M 4.25 6
        C 4.44 6 4.6 5.79 4.6 5.53
        C 4.6 5.27 4.44 5.05 4.25 5.05
        C 4.05 5.05 3.89 5.27 3.89 5.53
        C 3.89 5.79 4.05 6 4.25 6
        Z
        M 6.76 6
        C 6.95 6 7.11 5.79 7.11 5.53
        C 7.11 5.27 6.95 5.05 6.76 5.05
        C 6.56 5.05 6.4 5.27 6.4 5.53
        C 6.4 5.79 6.56 6 6.76 6
        Z"></path>
        </g>
            
        </defs>

        <g id="walls">
        {border_paths}
        </g>

        <g id="food">
        {food}
        </g>

        <g id="bots">
        {bots}
        </g>

        </svg>
        """

        filename = self.folder / f"pelita-{self.index:04d}.svg"
        _logger.info(f"Writing SVG file {filename}.")
        filename.write_text(template)
        self.index += 1


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
            as_json = json.dumps(message)
            self.sock.send_unicode(as_json, flags=zmq.NOBLOCK)

    def show_state(self, game_state):
        self._send(game_state)


class DumpingViewer:
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
        if winning_team in (0, 1):
            winner = state['team_names'][winning_team]
            loser = state['team_names'][1 - winning_team]
            winner_score = state['score'][winning_team]
            loser_score = state['score'][1 - winning_team]
            msg = f"Finished. '{winner}' won over '{loser}'. ({winner_score}:{loser_score})"
        elif winning_team == 2:
            t1, t2 = state['team_names']
            s1, s2 = state['score']
            msg = f"Finished. '{t1}' and '{t2}' had a draw. ({s1}:{s2})"
        else:
            return

        # We must flush, else our forceful stopping of Tk
        # won't let us pipe it.
        print(msg, flush=True)
