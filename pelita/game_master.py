import pelita.universe as uni
import random

class GameMaster(object):

    def __init__(self, layout, number_bots, game_time):
        self.universe = uni.create_CTFUniverse(layout, number_bots)
        self.game_time = game_time
        self.players = [None] * number_bots
        self.viewers = []

    def register_player(self,index, player):
        if player.__class__.get_move.__func__ == \
            AbstractPlayer.get_move.__func__:
                raise TypeError("Player %s does not override 'get_move()'."
                        % player.__class__)
        self.players[index] = player
        player.set_initial(self.universe)

    def register_viewer(self, viewer):
        if viewer.__class__.observe.__func__ == \
            AbstractViewer.observe.__func__:
                raise TypeError("Viewer %s does not override 'observe()'."
                        % viewer.__class__)
        self.viewers.append(viewer)

    def play(self):
        for gt in range(self.game_time):
            for i,p in enumerate(self.players):
                move = p.get_move(self.universe)
                events = self.universe.move_bot(i, move)
                for v in self.viewers:
                    v.observe(gt, i, self.universe, events)
                if any([isinstance(e, uni.TeamWins) for e in events]):
                    return

class AbstractViewer(object):

    def observe(self, round_, turn, universe, events):
        raise NotImplementedError(
                "You must override the 'observe' method in your viewer")

class AsciiViewer(AbstractViewer):

    def observe(self, round_, turn, universe, events):
        print ("Round: %i Turn: %i Score: %i:%i"
        % (round_, turn, universe.teams[0].score, universe.teams[1].score))
        print ("Events: %r" % events)
        print universe.as_str()
        if any([isinstance(e, uni.TeamWins) for e in events]):
            team_wins_event = filter(lambda x: isinstance(x, uni.TeamWins), events)[0]
            print ("Game Over: Team: '%s' wins!" %
            universe.teams[team_wins_event.winning_team_index].name)

class AbstractPlayer(object):

    def get_move(self, universe):
        raise NotImplementedError(
                "You must override the 'get_move' method in your player")

class RandomPlayer(AbstractPlayer):

    def __init__(self, index):
        self.index = index

    def set_initial(self, universe):
        pass

    def get_move(self, universe):
        legal_moves = universe.get_legal_moves(universe.bots[self.index].current_pos)
        return random.choice(legal_moves.keys())

