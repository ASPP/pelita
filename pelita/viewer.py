""" The observers. """

import pelita.universe as uni


class AbstractViewer(object):

    def observe(self, round_, turn, universe, events):
        raise NotImplementedError(
                "You must override the 'observe' method in your viewer")


class AsciiViewer(AbstractViewer):

    def observe(self, round_, turn, universe, events):
        print ("Round: %i Turn: %i Score: %i:%i"
        % (round_, turn, universe.teams[0].score, universe.teams[1].score))
        print ("Events: %r" % events)
        print universe.compact_str
        if any(isinstance(e, uni.TeamWins) for e in events):
            team_wins_event = filter(lambda x: isinstance(x, uni.TeamWins), events)[0]
            print ("Game Over: Team: '%s' wins!" %
            universe.teams[team_wins_event.winning_team_index].name)
