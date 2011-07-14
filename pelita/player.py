""" Base classes for player implementations. """

from pelita.universe import stop
import random


class AbstractPlayer(object):

    def _set_index(self, index):
        """ Called by the GameMaster to set this Players index.

        Parameters
        ----------
        index : int
            this players index

        """
        self._index = index

    def _set_initial(self, universe):
        """ Called by the GameMaster on initialisation.

        Parameters
        ----------
        universe : Universe
            the initial state of the universe

        """
        self.universe_states = []
        self.universe_states.append(universe)

    def set_initial(self, universe):
        """ Subclasses can override this if desired. """
        pass

    def _get_move(self, universe):
        """ Called by the GameMaster to obtain next move.

        This will add the universe to the list of universe_states and then call
        `self.get_move()`.

        Parameters
        ----------
        universe : Universe
            the universe in its current state.

        """
        self.universe_states.append(universe)
        return self.get_move(universe)

    def get_move(self, universe):
        raise NotImplementedError(
                "You must override the 'get_move' method in your player")
    @property
    def me(self):
        """ The Bot object this Player controls.

        Returns
        -------
        me : Bot
            the bot controlled by this player
        """
        self.universe_states[-1].bots[self._index]


class StoppingPlayer(AbstractPlayer):
    """ A Player that just stands still. """

    def get_move(self, universe):
        return stop


class RandomPlayer(AbstractPlayer):
    """ A player that makes moves at random. """

    def get_move(self, universe):
        legal_moves = universe.get_legal_moves(
                universe.bots[self._index].current_pos)
        return random.choice(legal_moves.keys())
