
import collections
import random

from . import AbstractTeam
from .. import datamodel


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
            team_move = args[1]
        else:
            self.team_name = ""
            team_move = args[0]

        self._team_move = team_move

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

        #: Storage for the team state
        self._team_state = {}
        self._team_game = Game([None, None], self._team_state)

        #: Storage for the random generator
        self._bot_random = {}

        for bot in team_bots:
            # We could call the function with a flag that tells the player
            # that it is the initial call. But then the player will have to check
            # for themselves in each round.
            #player._set_initial(universe, game_state)

            # we take the bot’s index as a value for the seed_offset
            self._bot_random[bot.index] = random.Random(game_state["seed"] + bot.index)

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
            'maze': universe.maze,
            'teams': [team._to_json_dict() for team in universe.teams],
            'bots': [bot._to_json_dict() for bot in universe.bots],
            'game_state': game_state,
            'bot_to_play': bot_id,
        }

        maze = universe.maze

        homezones = [
            Homezone((0, 0), (maze.width // 2 - 1, maze.height - 1)),
            Homezone((maze.width // 2, 0), (maze.width - 1, maze.height - 1))
        ]

        # Everybody only knows their own rng
        rng = self._bot_random[bot_id]

        bots = []
        for uni_bot in universe.bots:
            position = uni_bot.current_pos
            initial_position = uni_bot.initial_pos
            is_noisy = uni_bot.noisy
            homezone = homezones[uni_bot.team_index]
            score = universe.teams[uni_bot.team_index].score

            food = [f for f in universe.food if f in homezone]

            round = game_state['round_index']
            is_left = uni_bot.team_index == 0
            bot = Bot(uni_bot.index, position, initial_position, maze, homezone, food, is_noisy, score, rng, round, is_left, datadict)
            bots.append(bot)

        for bot in bots:
            bot._bots = bots

        me = bots[bot_id]
        turn = bot_id // 2
        if bot_id % 2 == 0:
            team = bots[0::2]
        else:
            team = bots[1::2]
        
        self._team_game.team[:] = team
        move = self._team_move(turn, self._team_game)
        print(move)

        # restore the team state
        self._team_state = self._team_game.state

        return {
            "move": move,
            "say": me._say
        }

    def __repr__(self):
        return "Team(%r, %s)" % (self.team_name, repr(self._team_move))

# @dataclass
class Game:
    def __init__(self, team, state):
        self.team = team
        self.state = state


class Homezone(collections.Container):
    def __init__(self, pos1, pos2):
        self.pos1 = pos1
        self.pos2 = pos2

    def __contains__(self, item):
        return (self.pos1[0] <= item[0] <= self.pos2[0]) and (self.pos1[1] <= item[1] <= self.pos2[1])


class Bot:
    def __init__(self, index, position, initial_position, maze, homezone, food, is_noisy, score, random, round, is_left, datadict):
        self._bots = None
        self._say = None
        self._initial_position = initial_position

        self.random = random
        # TODO
        self.position = position
        self.walls = maze
        self.legal_moves = []

        for move in [(-1, 0), (1, 0), (0, 1), (0, -1)]:
            new_pos = (self.position[0] + move[0], self.position[1] + move[1]) 
            if not self.walls[new_pos]:
                self.legal_moves.append(move)

        self.is_noisy = is_noisy
        # TODO: Homezone could be a mesh object …
        self.homezone = homezone
        self.food = food
        self.score  = score
        self.index  = index
        self.round = round
        self.is_left = is_left

    @property
    def other(self):
        other_index = (self.index + 2) % 4
        return self._bots[other_index]

    @property
    def enemies(self):
        enemy1_index = (self.index + 1) % 2
        enemy2_index = (self.index + 1) % 2 + 2
        return [self._bots[enemy1_index], self._bots[enemy2_index]]

    def say(self, text):
        self._say = text

    def get_direction(self, position):
        direction = (position[0] - self.position[0], position[1] - self.position[1])
        return direction

def _rebuild_universe(bots):
    # TODO
    for idx, b in enumerate(bots):
        homezone = b.homezone.pos1[0], b.homezone.pos2[0]

        bot = datamodel.Bot(idx,
                            initial_pos=b._initial_position,
                            team_index=idx%2,
                            homezone=homezone,
                            current_pos=b.position,
                            noisy=b.is_noisy)
        bots.append(bot)
    teams = []

    maze = bots[0].walls
    food = bots[0].food + bots[0].enemy1.food

    return datamodel.CTFUniverse(maze, food, teams, bots)


def new_style_team(module):
    """ Looks for a new-style team in `module`.
    """
    # look for a new-style team
    move = getattr(module, "move")
    name = getattr(module, "TEAM_NAME")
    if not callable(move):
        raise TypeError("move is not a function")
    if type(name) is not str:
        raise TypeError("TEAM_NAME is not a string")
    return lambda: Team(name, move)
