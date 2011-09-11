# -*- coding: utf-8 -*-

""" The observers. """

from pelita import datamodel

__docformat__ = "restructuredtext"


class AbstractViewer(object):
    def set_initial(self, universe):
        """ This method is called when the first universe is ready.
        """
        pass

    def observe(self, round_, turn, universe, events):
        raise NotImplementedError(
                "You must override the 'observe' method in your viewer")

class DevNullViewer(object):
    """ A viewer that simply ignores everything. """
    def set_initial(self, universe):
        pass

    def observe(self, round_, turn, universe, events):
        pass

class AsciiViewer(AbstractViewer):

    def observe(self, round_, turn, universe, events):
        print ("Round: %r Turn: %r Score: %r:%r"
        % (round_, turn, universe.teams[0].score, universe.teams[1].score))
        print ("Events: %r" % [str(e) for e in events])
        print universe.compact_str
        if datamodel.TeamWins in events:
            team_wins_event = events.filter_type(datamodel.TeamWins)[0]
            print ("Game Over: Team: '%s' wins!" %
            universe.teams[team_wins_event.winning_team_index].name)
