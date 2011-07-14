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
    def current_uni(self):
        """ The current Universe.

        Returns
        -------
        universe : Universe
            the current Universe

        """
        return self.universe_states[-1]

    @property
    def me(self):
        """ The Bot object this Player controls.

        Returns
        -------
        me : Bot
            the bot controlled by this player

        """
        return self.current_uni.bots[self._index]

    @property
    def team_bots(self):
        """ A list of Bots that are on this players team.

        Returns
        -------
        team_mates : list of Bot objects
            the team mates

        """
        this_team = [self.current_uni.bots[i] for i in
            self.current_uni.teams[self._index].bots]
        this_team.pop(self._index)
        return this_team

    @property
    def enemy_bots(self):
        """ A list of enemy Bots.

        Returns
        -------
        enemy_bots : list of Bot objects
            all Bots on all enemy teams
        """
        return self.current_uni.enemy_bots(self.me.team_index)

    @property
    def current_pos(self):
        """ The current position of this bot.

        Returns
        -------
        current_pos : tuple of (int, int)
            the current position (x, y) of this bot
        """
        return self.me.current_pos

    @property
    def initial_pos(self):
        """ The initial_pos of this bot.

        Returns
        -------
        initial_pos : tuple of (int, int)
            the initial position (x, y) of this bot

        """
        return self.me.initial_pos

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
