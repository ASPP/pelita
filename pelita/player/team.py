
from . import AbstractTeam


class Team(AbstractTeam):
    """ Simple class used to register an arbitrary number of (Abstract-)Players.

    Each Player is used to control a Bot in the Universe.

    SimpleTeam transforms the `set_initial` and `get_move` messages
    from the GameMaster into calls to the user-supplied functions.

    Parameters
    ----------
    team_name :
        the name of the team (optional)
    players : functions with signature (datadict, storage) -> move
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

        self._players = players
        self._bot_players = {}

        #: The storage dict that can be used to exchange data between the players
        # and between rounds.
        self.storage = {}

    def set_initial(self, team_id, universe, game_state):
        """ Sets the bot indices for the team and returns the team name.
        Currently, we do not call _set_initial on the user side.

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
            # TODO: This _index is obviously not visible from inside the functions,
            # therefore this information will have to be added to the datadict in each
            # call inside get_move.
            # TODO: This will fail for bound methods.
            player._index = bot.index

            # TODO: Should we tell the player about the initial universe?
            # We could call the function with a flag that tells the player
            # that it is the initial call. But then the player will have to check
            # for themselves in each round.
            #player._set_initial(universe, game_state)

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

        # We prepare a dict-only representation of our universe and game state.
        # This forces us to rewrite all functions for the user API and avoids having to
        # look into the documentation for our nested datamodel APIself.
        # Once we settle on a useable representation, we can then backport this to
        # the datamodel as well.
        datadict = {
            'food': universe.food,
            'maze': universe.maze._to_json_dict(),
            'teams': [team._to_json_dict() for team in universe.teams],
            'bots': [bot._to_json_dict() for bot in universe.bots],
            'game_state': game_state,
            'bot_to_play': bot_id,
        }


        print(datadict)

        # TODO: Transform the datadict in a way that makes it more practical to use,
        # reduces unnecessary redundancy but still avoids recalculations for simple things

        # TODO: What to do with the random seed?

        # TODO: How are we saying things? Should we have a reserved index in the storage dict
        # that can be used for that? storage['__say'] = "Blah"


        move = self._bot_players[bot_id](datadict, self.storage)
        return {
            "move": move,
        #    "say": ???
        }

    def __repr__(self):
        return "Team(%r, %s)" % (self.team_name, ", ".join(repr(p) for p in self._players))
