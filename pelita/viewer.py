# -*- coding: utf-8 -*-

""" The observers. """

import abc
import sys

from .messaging.json_convert import json_converter

__docformat__ = "restructuredtext"


class AbstractViewer(object, metaclass=abc.ABCMeta):
    def set_initial(self, universe):
        """ This method is called when the first universe is ready.
        """
        pass

    @abc.abstractmethod
    def observe(self, universe, game_state):
        pass

class DevNullViewer(AbstractViewer):
    """ A viewer that simply ignores everything. """
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
                universe.teams[winning_team_idx].name))

class DumpingViewer(AbstractViewer):
    """ A viewer which dumps to a given stream.
    """
    def __init__(self, stream):
        self.stream = stream

    def set_initial(self, universe):
        self.stream.write(json_converter.dumps({"universe": universe}))
        self.stream.write("\x04")

    def observe(self, universe, game_state):
        kwargs = {
            "universe": universe,
            "game_state": game_state
        }

        self.stream.write(json_converter.dumps(kwargs))
        self.stream.write("\x04")
