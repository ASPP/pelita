# -*- coding: utf-8 -*-

""" The observers. """

import abc

from .messaging.json_convert import json_converter

__docformat__ = "restructuredtext"


class AbstractViewer(object):
    __metaclass__ = abc.ABCMeta

    def set_initial(self, universe):
        """ This method is called when the first universe is ready.
        """
        pass

    @abc.abstractmethod
    def observe(self, universe, events):
        pass

class DevNullViewer(AbstractViewer):
    """ A viewer that simply ignores everything. """
    def observe(self, universe, game_state):
        pass

class AsciiViewer(AbstractViewer):
    """ A viewer that dumps ASCII charts on stdout. """

    def observe(self, universe, game_state):
        print ("Round: %r Turn: %r Score: %r:%r"
        % (game_state["round_index"], game_state["bot_id"], universe.teams[0].score, universe.teams[1].score))
        print ("Game State: %r") % game_state
        print universe.compact_str
        winning_team_idx = game_state.get("team_wins")
        if winning_team_idx is not None:
            print ("Game Over: Team: '%s' wins!" %
                universe.teams[winning_team_idx].name)

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
