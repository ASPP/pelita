from pelita import datamodel
from pelita.player import AbstractPlayer, SimpleTeam


class RandomExplorerPlayer(AbstractPlayer):
    """ Least visited random player. Will prefer moving to a position it’s never seen before. """
    def set_initial(self):
        self.visited = []

    def get_move(self):
        if self.current_pos in self.visited:
            self.visited.remove(self.current_pos)
        self.visited.insert(0, self.current_pos)

        moves = dict(self.legal_moves)
        for pos in self.visited:
            if len(moves) == 1:
                return list(moves.keys())[0]
            if len(moves) == 0:
                return datamodel.stop
            moves = {k: v for k, v in moves.items() if pos != v}
        # more than one move left
        return self.rnd.choice(list(moves.keys()))

def factory():
    return SimpleTeam("Random Explorer Players", RandomExplorerPlayer(), RandomExplorerPlayer())
