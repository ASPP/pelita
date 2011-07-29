""" The controller """

import pelita.datamodel as uni
from pelita.player import AbstractPlayer
from pelita.viewer import AbstractViewer

__docformat__ = "restructuredtext"


class GameMaster(object):
    """ Controller of player moves and universe updates.

    This object coordinates the moves of the player implementations with the
    updating of the universe.

    Parameters
    ----------
    universe : Universe
        the game state
    game_time : int
        the total permitted number of rounds
    number_bots : int
        the total number of bots
    players : list of subclasses of AbstractPlayer
        the player implementations
    viewers : list of subclasses of AbstractViewer
        the viewers that are observing this game

    """
    def __init__(self, layout, number_bots, game_time):
        self.universe = uni.create_CTFUniverse(layout, number_bots)
        self.game_time = game_time
        self.number_bots = number_bots
        self.players = []
        self.viewers = []

    def register_player(self, player):
        """ Register a client player implementation.

        Parameters
        ----------
        player : subclass of AbstractPlayer
            the concrete player implementation

        """
        if (player.__class__.get_move.__func__ ==
                AbstractPlayer.get_move.__func__):
            raise TypeError("Player %s does not override 'get_move()'."
                % player.__class__)
        self.players.append(player)
        player._set_index(len(self.players) - 1)
        player._set_initial(self.universe)

    def register_viewer(self, viewer):
        """ Register a viewer to display the game state as it progresses.

        Parameters
        ----------
        viewer : subclass of AbstractViewer

        """
        if (viewer.__class__.observe.__func__ ==
                AbstractViewer.observe.__func__):
            raise TypeError("Viewer %s does not override 'observe()'."
                    % viewer.__class__)
        self.viewers.append(viewer)

    # TODO the game winning detection should be refactored

    def play(self):
        """ Play a whole game. """
        if self.number_bots != len(self.players):
            raise IndexError(
                "GameMaster is configured for %i players, but only %i are registerd " 
                % (self.number_bots, len(self.players)))
        for gt in range(self.game_time):
            if not self.play_round(gt):
                return

    def play_round(self, current_game_time):
        """ Play only a single round.

        A single round is defined as all bots moving once.

        Parameters
        ----------
        current_game_time : int
            the number of this round

        """
        for i, p in enumerate(self.players):
            move = p._get_move(self.universe)
            events = self.universe.move_bot(i, move)
            for v in self.viewers:
                v.observe(current_game_time, i, self.universe, events)
            if uni.TeamWins in events:
                return False
        return True
