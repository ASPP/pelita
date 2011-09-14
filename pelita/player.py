# -*- coding: utf-8 -*-

""" Base classes for player implementations. """

import os
import random
import sys
import math
from .datamodel import stop, Free, diff_pos
from .graph import AdjacencyList, NoPathException

__docformat__ = "restructuredtext"

class SimpleTeam(object):
    """ Simple class used to register an arbitrary number of Players.

    Each Player is used to control a Bot in the Universe.

    Parameters
    ----------
    team_name :
        the name of the team (optional)
    players :
        the Players who shall join this SimpleTeam
    """
    def __init__(self, *args):
        if not args:
            raise ValueError("No teams given.")

        if isinstance(args[0], basestring):
            self.team_name = args[0]
            players = args[1:]
        else:
            self.team_name = ""
            players = args[:]

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
    def other_team_bots(self):
        """ A list of Bots that are on this players team.

        Returns
        -------
        other_team_bots : list of Bot objects
            the team mates, excluding this Player's Bot

        """
        return self.current_uni.other_team_bots(self._index)

    @property
    def team_bots(self):
        """ A list of all Bots that are on this Player's Bot's Team.

        Returns
        -------
        team_bots : list of Bot objects
            the team mates, including this Player's Bot
        """
        return self.current_uni.team_bots(self.me.team_index)

    @property
    def team_border(self):
        """ Positions of the border positions.
        These are the last positions in the zone of the team.

        Returns
        -------
        team_border : list of tuple of (int, int)
            the border positions

        """
        return self.current_uni.team_border(self.me.team_index)

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


class IOBoundPlayer(AbstractPlayer):
    """ IO Bound player that crawls the file system. """

    def get_move(self):
        count = 0
        self.timeouted = False
        for root, dirs, files in os.walk('/'):
            for f in files:
                try:
                    os.stat(os.path.join(root, f))
                except OSError:
                    pass
                finally:
                    count += 1
                    if count % 1000 == 0:
                        sys.stdout.write('.')
                        sys.stdout.flush()
                    if not self.timeouted and self.previous_pos != self.current_pos:
                        print "Crawling done and timeout received %i" % count
                        self.timeouted = True

class MoveExceptionPlayer(AbstractPlayer):
    """ Player that raises an Exception on get_move(). """

    def get_move(self):
        raise Exception("Exception from MoveExceptionPlayer.")


class InitialExceptionPlayer(AbstractPlayer):
    """ Player that raises an Exception on set_initial(). """

    def set_initial(self):
        raise Exception("Exception from InitialExceptionPlayer.")

    def get_move(self):
        pass

class CPUBoundPlayer(AbstractPlayer):
    """ Player that does loads of computation. """

    def get_move(self):
        self.timeouted = False
        total = 0.0
        count = 0
        for i in xrange(sys.maxint):
            total += i*i
            total = math.sin(total)
            count += 1
            if count % 1000 == 0:
                sys.stdout.write('.')
                sys.stdout.flush()
            if not self.timeouted and self.previous_pos != self.current_pos:
                print "Crawling done and timeout received %i" % count
                self.timeouted = True



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

    The adjacency lits representation (AdjacencyList) and breadth first search
    (AdjacencyList.bfs) are imported from pelita.graph.

    * [1] http://en.wikipedia.org/wiki/Adjacency_list
    * [2] http://en.wikipedia.org/wiki/Breadth-first_search

    """
    def set_initial(self):
        # Before the game starts we initialise our adjacency list.
        self.adjacency = AdjacencyList(self.current_uni)
        self.current_path = self.bfs_food()

    def bfs_food(self):
        """ Breadth first search for food.

        Returns
        -------
        path : a list of tuples (int, int)
            The positions (x, y) in the path from the current position to the
            closest food. The first element is the final destination.

        """
        try:
            return self.adjacency.bfs(self.current_pos, self.enemy_food)
        except NoPathException:
            return [self.current_pos]

    def get_move(self):
        if self.current_pos == self.initial_pos:
            # we have probably been killed
            # reset the path
            self.current_path = None
        if not self.current_path:
            self.current_path = self.bfs_food()
        new_pos = self.current_path.pop()
        try:
            return diff_pos(self.current_pos, new_pos)
        except ValueError:
            # If there was a timeout, and we are no longer where we think we
            # were, calculate a new path.
            self.current_path = None
            return self.get_move()

class BasicDefensePlayer(AbstractPlayer):
    """ A crude defensive player.

    Will move towards the border, and as soon as it notices enemies in its
    territory, it will start to track them. When it kills the enemy it returns
    to the border and waits there for more. Like the BFSPlayer this player
    stores the maze as an adjacency list [1] but uses the breadth first search [2] to
    find the closest position on the border.  However it additionally uses the
    A* (A Star) search [3] to find the shortest path to its target.

    The adjacency lits representation (AdjacencyList) and A* search
    (AdjacencyList.a_star) are imported from pelita.graph.

    * [1] http://en.wikipedia.org/wiki/Adjacency_list
    * [2] http://en.wikipedia.org/wiki/Breadth-first_search
    * [3] http://en.wikipedia.org/wiki/A*_search_algorithm

    """
    def set_initial(self):
        self.adjacency = AdjacencyList(self.current_uni)
        self.path = self.path_to_border
        self.tracking = None

    @property
    def path_to_border(self):
        """ Path to the closest border position. """
        return self.adjacency.bfs(self.current_pos, self.team_border)

    @property
    def path_to_target(self):
        """ Path to the target we are currently tracking. """
        return self.adjacency.a_star(self.current_pos,
                self.tracking_target.current_pos)

    @property
    def tracking_target(self):
        """ Bot object we are currently tracking. """
        return self.current_uni.bots[self.tracking]

    def get_move(self):
        # if we were killed, for whatever reason, reset the path
        if self.current_pos == self.initial_pos:
            self.current_path = self.path_to_border
        # if we are not currently tracking anything
        if not self.tracking:
            # check the enemy positions
            possible_targets = [enemy for enemy in self.enemy_bots
                    if self.team.in_zone(enemy.current_pos)]
            if possible_targets:
                # get the path to the closest one
                closest_enemy = min([(len(self.adjacency.a_star(self.current_pos,
                    enemy.current_pos)),enemy) for enemy in possible_targets])
                # track that bot by using its index
                self.tracking = closest_enemy[1].index
                self.path = self.path_to_target
            else:
                # otherwise keep going if we aren't already underway
                if not self.path:
                    self.path = self.path_to_border
        elif self.tracking:
            # if the enemy is no longer in our zone
            if not self.team.in_zone(self.tracking_target.current_pos):
                self.tracking = None
                self.path = self.path_to_border
            # otherwise update the path to the target
            else:
                self.path = self.path_to_target
        # if something above went wrong, just stand still
        if not self.path:
            return stop
        else:
            return diff_pos(self.current_pos, self.path.pop())
