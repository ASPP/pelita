
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
        walls = [pos for pos, is_wall in universe.maze.items() if is_wall]

        homezones = create_homezones(maze.width, maze.height)
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
            is_blue = uni_bot.team_index == 0
            bot = Bot(
                bot_index=uni_bot.index,
                position=position,
                initial_position=initial_position,
                walls=walls,
                homezone=homezone,
                food=food,
                is_noisy=is_noisy,
                score=score,
                random=rng,
                round=round,
                is_blue=is_blue)
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

    def _repr_html_(self):
        bot = self.team[0]
        width = max(bot.walls)[0] + 1
        height = max(bot.walls)[1] + 1

        from io import StringIO
        with StringIO() as out:
            out.write("<table>")
            for y in range(height):
                out.write("<tr>")
                for x in range(width):
                    if (x, y) in bot.walls:
                        bg = 'style="background-color: {}"'.format(
                            "rgb(94, 158, 217)" if x < width // 2 else
                            "rgb(235, 90, 90)")
                    else:
                        bg = ""
                    out.write("<td %s>" % bg)
                    if (x, y) in bot.walls: out.write("#")
                    if (x, y) in bot.food: out.write('<span style="color: rgb(247, 150, 213)">●</span>')
                    if (x, y) in bot.enemy[0].food: out.write('<span style="color: rgb(247, 150, 213)">●</span>')
                    for idx in range(4):
                        if bot._bots[idx].position == (x, y): out.write(str(idx))
                    out.write("</td>")
                out.write("</tr>")
            out.write("</table>")
            return out.getvalue()

def create_homezones(width, height):
    return [
        [(x, y) for x in range(0, width // 2)
                for y in range(0, height)],
        [(x, y) for x in range(width // 2, width)
                for y in range(0, height)]
    ]


class Bot:
    def __init__(self, *, bot_index, position, initial_position, walls, homezone, food, is_noisy, score, random, round, is_blue):
        self._bots = None
        self._say = None
        self._initial_position = initial_position

        self.random = random
        # TODO
        self.position = position
        self.walls = walls

        self.is_noisy = is_noisy
        # TODO: Homezone could be a mesh object …
        self.homezone = homezone
        self.food = food
        self.score  = score
        self.bot_index  = bot_index
        self.round = round
        self.is_blue = is_blue

    @property
    def legal_moves(self):
        legal_moves = []

        for move in [(-1, 0), (1, 0), (0, 1), (0, -1)]:
            new_pos = (self.position[0] + move[0], self.position[1] + move[1])
            if not new_pos in self.walls:
                legal_moves.append(move)

        return legal_moves

    @property
    def other(self):
        other_index = (self.bot_index + 2) % 4
        return self._bots[other_index]

    @property
    def enemy(self):
        enemy1_index = (self.bot_index + 1) % 2
        enemy2_index = (self.bot_index + 1) % 2 + 2
        return [self._bots[enemy1_index], self._bots[enemy2_index]]

    def say(self, text):
        self._say = text

    def get_move(self, position):
        """ Return the move needed to get to the given position.

        Raises
        ======
        ValueError
            If the position cannot be reached by a legal move
        """
        direction = (position[0] - self.position[0], position[1] - self.position[1])
        if direction not in self.legal_moves:
            raise ValueError("Cannot reach position %s (would have been: %s)." % (position, direction))
        return direction

    def get_position(self, move):
        """ Return the position reached with the given move

        Raises
        ======
        ValueError
            If the move is not legal.
        """
        if move not in self.legal_moves:
            raise ValueError("Move %s is not legal." % move)
        position = (move[0] + self.position[0], move[1] + self.position[1])
        return position


def _rebuild_universe(bots):
    uni_bots = []
    for idx, b in enumerate(bots):
        homezone = (min(b.homezone)[0], max(b.homezone)[0] + 1)

        bot = datamodel.Bot(idx,
                            initial_pos=b._initial_position,
                            team_index=idx%2,
                            homezone=homezone,
                            current_pos=b.position,
                            noisy=b.is_noisy)
        uni_bots.append(bot)

    uni_teams = [
        datamodel.Team(0, homezone[0], bots[0].score),
        datamodel.Team(1, homezone[1], bots[1].score)
    ]

    width = max(bots[0].walls)[0] + 1
    height = max(bots[0].walls)[1] + 1
    maze = datamodel.Maze(width, height)
    for pos in maze:
        if pos in bots[0].walls:
            maze[pos] = True
    food = bots[0].food + bots[0].enemy[1].food

    return datamodel.CTFUniverse(maze, food, uni_teams, uni_bots)


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
