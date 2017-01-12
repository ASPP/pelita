""" Base classes for player implementations. """

import abc
import pdb
import random
import time

from . import datamodel

class AbstractTeam(metaclass=abc.ABCMeta):
    """ Abstract team class.

    Players who want to write their own Team class (instead of using
    `SimpleTeam` together with a number of independent `AbstractPlayer` subclasses),
    should inherit from `AbstractTeam` (though this is not strictly necessary).
    """

    @abc.abstractmethod
    def set_initial(self, team_id, universe, game_state):
        """ Tells the team about its id and gives initial information
         about the universe and game state.

        Players who want write their own team class need to supply
        a method with the same signature.

        Parameters
        ----------
        team_id : int
            The id of the team
        universe : Universe
            The initial universe
        game_state : dict
            The initial game state

        Returns
        -------
        Team name : string
            The name of the team
        """

    @abc.abstractmethod
    def get_move(self, bot_id, universe, game_state):
        """ Requests a move from the bot with id `bot_id`.

        This method returns a dict with a key `move` and a value specifying the direction
        in a tuple. Additionally, a key `say` can be added with a textual value.

        Parameters
        ----------
        bot_id : int
            The id of the bot who needs to play
        universe : Universe
            The initial universe
        game_state : dict
            The initial game state

        Returns
        -------
        move : dict
        """


class SimpleTeam(AbstractTeam):
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

        if isinstance(args[0], str):
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
        """ Sets the bot indices for the team and tells each player
        about the universe and game state by calling `_set_index` and `_set_initial`.

        Parameters
        ----------
        team_id : int
            The id of the team
        universe : Universe
            The initial universe
        game_state : dict
            The initial game state

        Returns
        -------
        Team name : string
            The name of the team

        """

        # only iterate about those player which are in bot_players
        # we might have defined more players than we have received
        # indexes for.
        team_bots = universe.team_bots(team_id)

        if len(team_bots) > len(self._players):
            raise ValueError("Tried to set %d bot_ids with only %d Players." % (len(team_bots), len(self._players)))

        for bot, player in zip(team_bots, self._players):
            # tell the player its index
            player._set_index(bot.index)
            # tell the player about the initial universe
            player._set_initial(universe, game_state)
            self._bot_players[bot.index] = player

        return self.team_name

    def get_move(self, bot_id, universe, game_state):
        """ Requests a move from the Player who controls the Bot with id `bot_id`.

        This method returns a dict with a key `move` and a value specifying the direction
        in a tuple. Additionally, a key `say` can be added with a textual value.

        Parameters
        ----------
        bot_id : int
            The id of the bot who needs to play
        universe : Universe
            The initial universe
        game_state : dict
            The initial game state

        Returns
        -------
        move : dict
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

    def __repr__(self):
        return "SimpleTeam(%r, %s)" % (self.team_name, ", ".join(repr(p) for p in self._players))

class AbstractPlayer(metaclass=abc.ABCMeta):
    """ Base class for all user implemented Players. """

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

        self._current_state = game_state
        self.universe_states = []
        self._store_universe(universe)

        # we take the bot’s index as a default value for the seed_offset
        # this ensures that the bots differ in their actions
        seed_offset = getattr(self, "seed_offset", self._index)

        self.rnd = random.Random()
        if game_state.get("seed") is not None:
            self.rnd.seed(game_state["seed"] + seed_offset)

        self.set_initial()

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
        #: Used for the `time_spent` method.
        self.__time_in_get_move = time.monotonic()
        self._current_state = game_state
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
    def current_state(self):
        """ The current game state.

        Returns
        -------
        game_state : dict
            The current game_state dict
        """
        return self._current_state

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
    def team_bots(self):
        """ A list of all Bots that are on this Player's Bot's Team including
        the current bot.

        Returns
        -------
        team_bots : list of Bot objects
            the team mates, including this Player's Bot
        """
        return self.current_uni.team_bots(self.me.team_index)

    @property
    def other_team_bots(self):
        """ A list of Bots that are on this Player's team excluding the current
        bot.

        Please parse this method mentally as ‘other (team bots)’. These bots
        are not your enemies. See also: ``enemy_bots``.

        Returns
        -------
        other_team_bots : list of Bot objects
            the team mates, excluding this Player's Bot

        """
        return self.current_uni.other_team_bots(self._index)

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

        Please note that it is valid for this list to be empty during get_move.

        Returns
        -------
        team_food : list of position tuples (int, int)
            The positions (x, y) of food edible by the enemy

        """
        return self.current_uni.team_food(self.me.team_index)

    @property
    def enemy_food(self):
        """ Food owned by the enemy which can be eaten by this Player's bot.

        Please note that it is valid for this list to be empty during get_move.

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
    def enemy_name(self):
        """ The name of the enemy Team.
        (This information will not be available in set_initial).

        Returns
        -------
        enemy_name : string
            the name of the enemy team
        """
        return self.current_state["team_name"][self.enemy_team.index]

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
        return self.current_uni.legal_moves(self.current_pos)

    def time_spent(self):
        """ The approximate amount of time since `get_move` was
        called.

        Note: Due to delays in network communication and serialisation,
        this method is not completely reliable concerning the timeout
        handling. It may however be useful for debugging and as a
        rough estimation.

        Returns
        -------
        time_needed : float
            time in seconds
        """
        try:
            current_time = time.monotonic()
            return current_time - self.__time_in_get_move
        except AttributeError:
            return None


    def simulate_move(self, move):
        """ Simulate a move of the bot in a certain direction
        and return the new state and universe.

        Parameters
        ----------
        move : tuple of (int, int)
            direction to move in

        Returns
        -------
        (universe, game_state) : (universe, dict)
            the new universe and the new game_state

        Raises
        ------
        IllegalMoveException
            if the move is invalid or impossible

        """
        uni = self.current_uni.copy()
        new_state = uni.move_bot(self._index, move)
        return (uni, new_state)

    def say(self, text):
        """ Let the bot speak.

        Parameters
        ----------
        text : string
            the text to be shown in the Viewer.
        """
        self._say = text

    def __str__(self):
        return "%s(index=%r, current_pos=%r)" % (self.__class__.__name__,
                getattr(self, "_index", None),
                getattr(self, "current_pos", None))

class StoppingPlayer(AbstractPlayer):
    """ A Player that just stands still. """
    def get_move(self):
        return datamodel.stop

class SpeakingPlayer(AbstractPlayer):
    """ A player that makes moves at random and tells us about it. """

    def get_move(self):
        move = self.rnd.choice(list(self.legal_moves.keys()))
        self.say("Going %r." % (move,))
        return move

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
        if isinstance(moves, str):
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

class DebuggablePlayer(AbstractPlayer):
    """ Player which invokes pdb on each move. 

    Setting ``direction`` inside the debugger will change
    its behaviour.
    """
    def get_move(self):
        direction = datamodel.stop
        pdb.set_trace()
        return direction
