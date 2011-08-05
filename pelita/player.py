# -*- coding: utf-8 -*-

""" Base classes for player implementations. """

from pelita.datamodel import stop, Free, diff_pos
from collections import deque
import random

__docformat__ = "restructuredtext"

class SimpleTeam(object):
    """ Simple class used to register an arbitrary number of Players.

    Each Player is used to control a Bot in the Universe.

    Parameters
    ----------
    players : list of Players
        the Players who shall join this SimpleTeam
    """
    def __init__(self, *players):
        for player in players:
            if (player.__class__.get_move.__func__ == AbstractPlayer.get_move.__func__):
                raise TypeError("Player %s does not override 'get_move()'." % player.__class__)
        self._players = players
        self._bot_players = {}

    def _set_bot_ids(self, bot_ids):
        if len(bot_ids) > len(self._players):
            raise ValueError("Tried to set %d bot_ids with only %d Players." % (len(bot_ids), len(self._players)))
        for bot_id, player in zip(bot_ids, self._players):
            player._set_index(bot_id)
            self._bot_players[bot_id] = player

    def _set_initial(self, universe):
        # only iterate about those player which are in bot_players
        # we might have defined more players than we have received
        # indexes for.
        for player in self._bot_players.values():
            player._set_initial(universe)

    def _get_move(self, bot_idx, universe):
        """ Requests a move from the Player who controls the Bot with index `bot_idx`.
        """
        return self._bot_players[bot_idx]._get_move(universe)

class AbstractPlayer(object):
    """ Base class for all user implemented Players. """

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
        self.set_initial()

    def set_initial(self):
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
        return self.get_move()

    def get_move(self):
        """ Subclasses _must_ override this. """
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
    def team(self):
        """ The Team object this Players Bot is on.

        Returns
        -------
        team : Team
            the team of the bot controlled by this player

        """
        return self.current_uni.teams[self.me.team_index]

    @property
    def team_bots(self):
        """ A list of Bots that are on this players team.

        Returns
        -------
        team_bots : list of Bot objects
            the team mates

        """
        return self.current_uni.team_bots(self._index)

    @property
    def enemy_food(self):
        """ Food owned by the enemy which can be eaten by this players bot.

        Returns
        -------
        enemy_food : list of position tuples (int, int)
            The positions (x, y) of edible food

        """
        return self.current_uni.enemy_food(self.me.team_index)

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
    def previous_pos(self):
        """ The previous position of the bot.

        Returns
        -------
        previous_pos : tuple of (int, int)
            the previous position (x, y) of this bot
        """
        return self.universe_states[-2].bots[self._index].current_pos

    @property
    def initial_pos(self):
        """ The initial_pos of this bot.

        Returns
        -------
        initial_pos : tuple of (int, int)
            the initial position (x, y) of this bot

        """
        return self.me.initial_pos

    @property
    def legal_moves(self):
        """ The currently possible moves, and where they lead.

        Returns
        -------
        legal_moves : dict mapping moves to positions
            the currently legal moves
        """
        return self.current_uni.get_legal_moves(self.current_pos)

class StoppingPlayer(AbstractPlayer):
    """ A Player that just stands still. """

    def get_move(self):
        return stop


class RandomPlayer(AbstractPlayer):
    """ A player that makes moves at random. """

    def get_move(self):
        return random.choice(self.legal_moves.keys())

class TestPlayer(AbstractPlayer):
    """ A Player with predetermined set of moves.

    Parameters
    ----------
        moves : list of moves
            the moves to make in reverse (stack) order

    """

    def __init__(self, moves):
        self.moves = moves

    def get_move(self):
        return self.moves.pop()

class NQRandomPlayer(AbstractPlayer):
    """ Not-Quite-RandomPlayer that will move randomly but not stop or reverse. """

    def get_move(self):
        legal_moves = self.legal_moves
        # Remove stop
        try:
            del legal_moves[stop]
        except KeyError:
            pass
        # now remove the move that would lead to the previous_position
        # unless there is no where else to go.
        if len(legal_moves) > 1:
            for (k,v) in legal_moves.iteritems():
                if v == self.previous_pos:
                    break
            del legal_moves[k]
        # just in case, there is really no way to go to:
        if not legal_moves:
            return stop
        # and select a move at random
        return random.choice(legal_moves.keys())


class BFSPlayer(AbstractPlayer):
    """ This player uses breadth first search to always go to the closest food.

    This player uses an adjacency list [1] to store the topology of the
    maze. It will then do a breadth first search [2] to search for the
    closest food. When found, it will follow the determined path until it
    reaches the food. This continues until all food has been eaten or the
    enemy wins.

    [1] http://en.wikipedia.org/wiki/Adjacency_list
    [2] http://en.wikipedia.org/wiki/Breadth-first_search

    """
    def set_initial(self):
        # Before the game starts we initialise our adjacency list.
        # to begin with, we get the list of all free positions
        free_pos = self.current_uni.maze.pos_of(Free)
        # Here we use a generator on a dictionary to create adjacency list.
        self.adjacency = dict((pos, self.current_uni.get_legal_moves(pos).values())
                for pos in free_pos)
        self.current_path = self.bfs_food()

    def bfs_food(self):
        """ Breadth first search for food.

        Returns
        -------
        path : a list of tuples (int, int)
            The positions (x, y) in the path furthest to closest. The first
            element is the final destination.

        """
        # Initialise `to_visit` of type `deque` with current position.
        # We use a `deque` since we need to extend to the right
        # but pop from the left, i.e. its a fifo queue.
        to_visit = deque([self.current_pos])
        # `seen` is a list of nodes we have seen already
        # We append to right and later pop from right, so a list will do.
        # Order is important for the back-track later on, so don't use a set.
        seen = []
        while to_visit:
            current = to_visit.popleft()
            if current in seen:
                # This node has been seen, ignore it.
                continue
            elif current in self.enemy_food:
                # We found some food, break and back-track path.
                break
            else:
                # Otherwise keep going, i.e. add adjacent nodes to seen list.
                seen.append(current)
                to_visit.extend(self.adjacency[current])
        # Now back-track using seen to determine how we got here.
        # Initialise the path with current node, i.e. position of food.
        path = [current]
        while seen:
            # Pop the latest node in seen
            next_ = seen.pop()
            # If that's adjacent to the current node
            # it's in the path
            if next_ in self.adjacency[current]:
                # So add it to the path
                path.append(next_)
                # And continue back-tracking from there
                current = next_
        # The last element is the current position, we don't need that in our
        # path, so don't include it.
        return path[:-1]

    def get_move(self):
        if self.current_pos == self.initial_pos:
            # we have probably been killed
            # reset the path
            self.current_path = None
        if not self.current_path:
            self.current_path = self.bfs_food()
        new_pos = self.current_path.pop()
        return diff_pos(self.current_pos, new_pos)
