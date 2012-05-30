# -*- coding: utf-8 -*-

""" The observers. """

import abc

from . import datamodel
from .messaging.json_convert import json_converter

__docformat__ = "restructuredtext"


class AbstractViewer(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, geometry=None):
        pass

    def set_initial(self, universe):
        """ This method is called when the first universe is ready.
        """
        pass

    @abc.abstractmethod
    def observe(self, round_, turn, universe, events):
        pass

class DevNullViewer(AbstractViewer):
    """ A viewer that simply ignores everything. """
    def observe(self, round_, turn, universe, events):
        pass

class AsciiViewer(AbstractViewer):
    """ A viewer that dumps ASCII charts on stdout. """

    def observe(self, round_, turn, universe, events):
        print ("Round: %r Turn: %r Score: %r:%r"
        % (round_, turn, universe.teams[0].score, universe.teams[1].score))
        print ("Events: %r" % [str(e) for e in events])
        print universe.compact_str
        if datamodel.TeamWins in events:
            team_wins_event = events.filter_type(datamodel.TeamWins)[0]
            print ("Game Over: Team: '%s' wins!" %
            universe.teams[team_wins_event.winning_team_index].name)

class DumpingViewer(AbstractViewer):
    """ A viewer which dumps to a given stream.
    """
    def __init__(self, stream, **kwargs):
        super(DumpingViewer, self).__init__(**kwargs)
        self.stream = stream

    def set_initial(self, universe):
        self.stream.write(json_converter.dumps({"universe": universe}))
        self.stream.write("\x04")

    def observe(self, round_, turn, universe, events):
        kwargs = {
            "round_": round_,
            "turn": turn,
            "universe": universe,
            "events": events
        }

        self.stream.write(json_converter.dumps(kwargs))
        self.stream.write("\x04")
