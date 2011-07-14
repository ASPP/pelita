
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

