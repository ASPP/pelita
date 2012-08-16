# -*- coding: utf-8 -*-

""" Base classes for player implementations. """

import os
import random
import sys
import math
import abc
from . import datamodel
from .datamodel import Free, diff_pos
from .graph import AdjacencyList, NoPathException

__docformat__ = "restructuredtext"

SANE_PLAYERS = ['BFSPlayer',
                'BasicDefensePlayer',
                'NQRandomPlayer',
                'RandomPlayer']

class SimpleTeam(object):
    """ Simple class used to register an arbitrary number of (Abstract-)Players.

    Each Player is used to control a Bot in the Universe.

    SimpleTeam transforms the `set_initial` and `get_move` messages
    from the GameMaster into `_set_index`, `_set_initial` and `_get_move`
    messages on the Player.

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
            for method in ('_set_index', '_get_move', '_set_initial'):
                if not hasattr(player, method):
                    raise TypeError('player missing %s()' % method)

        self._players = players
        self._bot_players = {}

        self._remote_game = False
        self.remote_game = False

    def set_initial(self, team_id, universe, game_state):
        # only iterate about those player which are in bot_players
        # we might have defined more players than we have received
        # indexes for.
        team = universe.teams[team_id]

        if len(team.bots) > len(self._players):
            raise ValueError("Tried to set %d bot_ids with only %d Players." % (len(team.bots), len(self._players)))

        for bot_id, player in zip(team.bots, self._players):
            # tell the player its index
            player._set_index(bot_id)
            # tell the player about the initial universe
            player._set_initial(universe, game_state)
            self._bot_players[bot_id] = player

    def get_move(self, bot_id, universe, game_state):
        """ Requests a move from the Player who controls the Bot with id `bot_id`.
        """
        return self._bot_players[bot_id]._get_move(universe, game_state)

    @property
    def remote_game(self):
        return self._remote_game

    @remote_game.setter
    def remote_game(self, remote_game):
        self._remote_game = remote_game
        for player in self._players:
            player._remote_game = self._remote_game

class AbstractPlayer(object):
    """ Base class for all user implemented Players. """

    __metaclass__ =  abc.ABCMeta

    def _set_index(self, index):
        """ Called by SimpleTeam to set this Player's index.

        Parameters
        ----------
        index : int
            this Player's index

        """
        self._index = index

    def _set_initial(self, universe, game_state):
        """ Called by SimpleTeam on initialisation.

        Parameters
        ----------
        universe : Universe
            the initial state of the universe

        """
        if getattr(self, "_remote_game", None):
            self._store_universe = self._store_universe_ref
        else:
            self._store_universe = self._store_universe_copy

        self.current_state = game_state
        self.universe_states = []
        self._store_universe(universe)
        self.set_initial()

        # we take the bot’s index as a default value for the seed_offset
        # this ensures that the bots differ in their actions
        seed_offset = getattr(self, "seed_offset", self._index)
        self.rnd = random.Random()
        if game_state.get("seed") is not None:
            self.rnd.seed(game_state["seed"] + seed_offset)

    def set_initial(self):
        """ Subclasses can override this if desired. """
        pass

    def _store_universe_copy(self, universe):
        self.universe_states.append(universe.copy())

    def _store_universe_ref(self, universe):
        self.universe_states.append(universe)

    def _get_move(self, universe, game_state):
        """ Called by SimpleTeam to obtain next move.

        This will add the universe to the list of universe_states and then call
        `self.get_move()`.

        Parameters
        ----------
        universe : Universe
            the universe in its current state.

        """
        self.current_state = game_state
        self._store_universe(universe)
        self._say = ""
        move = self.get_move()
        return {
            "move": move,
            "say": self._say
        }

    @abc.abstractmethod
    def get_move(self):
        """ Subclasses _must_ override this. """

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
        """ The Team object this Player's Bot is on.

        Returns
        -------
        team : Team
            the team of the bot controlled by this player

        """
        return self.current_uni.teams[self.me.team_index]

    @property
    def other_team_bots(self):
        """ A list of Bots that are on this Player's team.

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
    def team_food(self):
        """ Food owned by the team which can be eaten by the enemy Player's bot.

        Returns
        -------
        team_food : list of position tuples (int, int)
            The positions (x, y) of food edible by the enemy

        """
        return self.current_uni.team_food(self.me.team_index)

    @property
    def enemy_food(self):
        """ Food owned by the enemy which can be eaten by this Player's bot.

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
    def enemy_team(self):
        """ The enemy Team.

        Returns
        -------
        enemy_team : Team object
            the enemy teams
        """
        return self.current_uni.enemy_team(self.me.team_index)

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

    def say(self, text):
        """ Let the bot speak.

        Parameters
        ----------
        text : string
            the text to be shown in the Viewer.
        """
        self._say = unicode(text, errors='ignore')

class StoppingPlayer(AbstractPlayer):
    """ A Player that just stands still. """
    def get_move(self):
        return datamodel.stop

class RandomPlayer(AbstractPlayer):
    """ A player that makes moves at random. """

    def get_move(self):
        return random.choice(self.legal_moves.keys())

class SpeakingPlayer(AbstractPlayer):
    """ A player that makes moves at random and tells us about it. """

    def get_move(self):
        move = random.choice(self.legal_moves.keys())
        self.say("Going %r." % (move,))
        return move

class SeededRandomPlayer(AbstractPlayer):
    """ A random player which uses the global seed. """
    def get_move(self):
        return self.rnd.choice(self.legal_moves.keys())

class TestPlayer(AbstractPlayer):
    """ A Player with predetermined set of moves.

    Parameters
    ----------
    moves : list of moves or str of shorthand symbols
        the moves to make in order, see notes below

    Notes
    -----
    The ``moves`` argument can either be a list of moves, e.g. ``[west, east,
    south, north, stop]`` or a string of shorthand symbols, where the equivalent
    of the previous example is: ``'><v^-'``.

    """


    _MOVES = {'^': datamodel.north,
              'v': datamodel.south,
              '<': datamodel.west,
              '>': datamodel.east,
              '-': datamodel.stop}

    def __init__(self, moves):
        if isinstance(moves, basestring):
            moves = (self._MOVES[move] for move in moves)
        self.moves = iter(moves)

    def get_move(self):
        try:
            return next(self.moves)
        except StopIteration:
            raise ValueError()

class RoundBasedPlayer(AbstractPlayer):
    """ A Player which makes a decision dependent on the round index
    in a dict or list. (Or anything which responds to moves[idx].)

    Parameters
    ----------
    moves : list or dict of moves
        the moves to make, a move is determined by moves[round]
    """
    def __init__(self, moves):
        self.moves = moves
        self.round_index = None

    def get_move(self):
        if self.round_index is None:
            self.round_index = 0
        else:
            self.round_index += 1

        try:
            return self.moves[self.round_index]
        except (IndexError, KeyError):
            return datamodel.stop

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
            del legal_moves[datamodel.stop]
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
            return datamodel.stop
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
        self.tracking_idx = None

    @property
    def path_to_border(self):
        """ Path to the closest border position. """
        try:
            return self.adjacency.bfs(self.current_pos, self.team_border)
        except NoPathException:
            return None

    @property
    def path_to_target(self):
        """ Path to the target we are currently tracking. """
        try:
            return self.adjacency.a_star(self.current_pos,
                    self.tracking_target.current_pos)
        except NoPathException:
            return None

    @property
    def tracking_target(self):
        """ Bot object we are currently tracking. """
        return self.current_uni.bots[self.tracking_idx]

    def get_move(self):
        # if we were killed, for whatever reason, reset the path
        if self.current_pos == self.initial_pos or self.path is None:
            self.path = self.path_to_border

        # First we need to check, if our tracked enemy is still
        # in our zone
        if self.tracking_idx is not None:
            # if the enemy is no longer in our zone
            if not self.team.in_zone(self.tracking_target.current_pos):
                self.tracking_idx = None
                self.path = self.path_to_border
            # otherwise update the path to the target
            else:
                self.path = self.path_to_target

        # if we are not currently tracking anything
        # (need to check explicity for None, because using 'if 
        # self.tracking_idx' would evaluate to True also when we are tracking
        # the bot with index == 0)
        if self.tracking_idx is None:
            # check the enemy positions
            possible_targets = [enemy for enemy in self.enemy_bots
                    if self.team.in_zone(enemy.current_pos)]
            if possible_targets:
                # get the path to the closest one
                try:
                    possible_paths = [(enemy, self.adjacency.a_star(self.current_pos, enemy.current_pos))
                                      for enemy in possible_targets]
                except NoPathException:
                    possible_paths = []
            else:
                possible_paths = []

            if possible_paths:
                closest_enemy, path = min(possible_paths,
                                          key=lambda enemy_path: len(enemy_path[1]))

                # track that bot by using its index
                self.tracking_idx = closest_enemy.index
                self.path = path
            else:
                # otherwise keep going if we aren't already underway
                if not self.path:
                    self.path = self.path_to_border

        # if something above went wrong, just stand still
        if not self.path:
            return datamodel.stop
        else:
            return diff_pos(self.current_pos, self.path.pop())
