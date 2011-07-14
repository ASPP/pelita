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
                if any(isinstance(e, uni.TeamWins) for e in events):
                    return

