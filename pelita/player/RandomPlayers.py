from pelita import datamodel
from pelita.player import AbstractPlayer, SimpleTeam


class RandomPlayer(AbstractPlayer):
    """ A player that makes moves at random. """

    def get_move(self):
        return self.rnd.choice(list(self.legal_moves.keys()))


class NQRandomPlayer(AbstractPlayer):
    """ Not-Quite-RandomPlayer that will move randomly but not stop or reverse. """

    def get_move(self):
        legal_moves = self.legal_moves
        # Remove stop
        try:
            del legal_moves[datamodel.stop]
        except KeyError:
            pass
        # now remove the move that would lead to the previous_position
        # unless there is no where else to go.
        if len(legal_moves) > 1:
            for (k,v) in legal_moves.items():
                if v == self.previous_pos:
                    break
            del legal_moves[k]
        # just in case, there is really no way to go to:
        if not legal_moves:
            return datamodel.stop
        # and select a move at random
        return self.rnd.choice(list(legal_moves.keys()))

def factory():
    return SimpleTeam("The Random Players", RandomPlayer(), NQRandomPlayer())
