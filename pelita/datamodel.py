""" The datamodel. """

from .containers import Mesh
from .graph import iter_adjacencies, new_pos
from .layout import Layout

north = (0, -1)
south = (0, 1)
west  = (-1, 0)
east  = (1, 0)
stop  = (0, 0)

class Team:
    """ A team of bots.

    Parameters
    ----------
    index : int
        the index of the team within the Universe
    zone : tuple of int (x_min, x_max)
        the homezone of this team
    score : int, optional, default = 0
        the score of this team

    """
    def __init__(self, index, zone, score=0):
        self.index = index
        self.zone = zone
        self.score = score

    def in_zone(self, position):
        """ Check if a position is within the zone of this team.

        Parameters
        ----------
        position : tuple of int (x, y)
            the position to check

        Returns
        -------
        is_in_zone : boolean
            True if the position is in the homezone and False otherwise

        """
        return self.zone[0] <= position[0] <= self.zone[1]

    def __repr__(self):
        return ('Team(%i, %s, score=%i)' %
                (self.index, self.zone, self.score))

    def __eq__(self, other):
        return type(self) == type(other) and self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not (self == other)

    def _to_json_dict(self):
        return {"index": self.index,
                "zone": self.zone,
                "score": self.score}

    @classmethod
    def _from_json_dict(cls, item):
        # need to convert the json list to a tuple
        item["zone"] = tuple(item["zone"])
        return cls(**item)

class Bot:
    """ A bot on a team.

    Parameters
    ----------
    index : int
        the index of this bot within the Universe
    initial_pos : tuple of int (x, y)
        the initial position for this bot
    team_index : int
        the index of the team that this bot is on
    homezone : tuple of int (x_min, x_max)
        the homezone of this team
    current_pos : tuple of int (x, y), optional
        the current position of this bot
        default = None (will be set to initial_pos)

    Attributes
    ----------
    in_own_zone : boolean, property
        True if in its own homezone and False otherwise
    is_destroyer : boolean, property
        True if a destroyer, False otherwise
    is_harvester : boolean, property
        not is_destroyer
    noisy : boolean
        True if the position is noisy, False if it is exact

    """
    def __init__(self, index, initial_pos, team_index, homezone,
            current_pos=None, noisy=False):
        self.index = index
        self.initial_pos = initial_pos
        self.team_index = team_index
        self.homezone = homezone
        if not current_pos:
            self.current_pos = self.initial_pos
        else:
            self.current_pos = current_pos
        self.noisy = noisy

    @property
    def in_own_zone(self):
        return self.homezone[0] <= self.current_pos[0] <= self.homezone[1]

    @property
    def is_destroyer(self):
        return self.in_own_zone

    @property
    def is_harvester(self):
        return not self.is_destroyer

    def _to_initial(self):
        """ Reset this bot to its initial position. """
        self.current_pos = self.initial_pos

    def __eq__(self, other):
        return type(self) == type(other) and self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not (self == other)

    def __repr__(self):
        return ('Bot(%i, %s, %i, %s , current_pos=%s, noisy=%r)' %
                (self.index, self.initial_pos, self.team_index,
                    self.homezone, self.current_pos, self.noisy))

    def _to_json_dict(self):
        return {"index": self.index,
                "initial_pos": self.initial_pos,
                "team_index": self.team_index,
                "homezone": self.homezone,
                "current_pos": self.current_pos,
                "noisy": self.noisy}

    @classmethod
    def _from_json_dict(cls, item):
        # need to convert the json list to a tuple
        for tupled_attr in ["initial_pos", "homezone", "current_pos"]:
            item[tupled_attr] = tuple(item[tupled_attr])
        return cls(**item)

Free = ' '
Wall = '#'
Food = '.'

maze_components = [Food, Free, Wall]

class Maze(Mesh):
    """ The `Maze` object holds the walls of the universe.

    Data is stored and given in row-based order, eg.

    >>> m = Maze(4, 3, data=[True, False, True, True] + [True, False, False, True] + 4*[True])

    specifies the maze

        # ##
        #  #
        ####

    Parameters
    ----------
    width : int
        the width of the maze
    height : int
        the height of the maze
    data : iterable of bools
        the walls of the maze (True) or free space (False) in row-based order

    Attributes
    ----------
    shape : (int, int)
        tuple of width and height

    """
    def __init__(self, width, height, data=None):
        if not data:
            data = [False] * (width * height)
        elif not all(isinstance(s, bool) for s in data):
            raise TypeError("Maze keyword argument 'data' should be a list of of " +\
                            "bools, not: %r" % data)
        super(Maze, self).__init__(width, height, data)

    @property
    def positions(self):
        """ The indices of positions in the Maze.

        Returns
        -------
        positions : list of tuple of (int, int)
            the positions (x, y) in the Maze

        """
        return list(self.keys())

def create_maze(layout_mesh):
    """ Transforms a layout_mesh into a Maze.

    Parameters
    ----------
    layout_mesh : Mesh of single char strings
        Mesh of single character strings describing the layout

    Returns
    -------
    maze : Maze
        the Maze

    """
    maze = Maze(layout_mesh.width, layout_mesh.height)
    food = []
    for pos, items in layout_mesh.items():
        if Wall in items:
            maze[pos] = True
        if Food in items:
            food.append(pos)
    return maze, food

def extract_initial_positions(mesh, number_bots):
    """ Extract initial positions from mesh.

    Also replaces the initial positions in the mesh with free spaces.

    Parameters
    ----------
    mesh : Mesh of characters
        the layout in mesh format
    number_bots : int
        the number of bots for which to find initial positions

    Returns
    -------
    initial pos : list of tuples
        the initial positions for all the bots
    """
    bot_ids = [str(i) for i in range(number_bots)]
    start = [(0, 0)] * number_bots
    for k, v in mesh.items():
        if v in bot_ids:
            start[int(v)] = k
            mesh[k] = Free
    return start


class UniverseException(Exception):
    """ Standard error in the Universe. """
    pass


class IllegalMoveException(Exception):
    """ Raised when a bot attempts to make an illegal move. """
    pass

class CTFUniverse:
    """ The Universe: representation of the game state.

    Parameters
    ----------
    maze : Maze object
        the maze
    teams : list of Team objects
        the teams
    bots : list of Bot objects
        the bots

    Attributes
    ----------
    bot_positions : list of tuple of ints (x, y), property
        the current position of all bots
    food_list : list of tuple of ints (x, y), property
        the positions of all edible food

    """

    @classmethod
    def create(cls, layout_str, number_bots):
        """ Factory to create a 2 team Capture The Flag Universe.

        Parameters
        ----------
        layout_str : str
            the string encoding the maze layout
        number_bots : int
            the number of bots in the game

        Raises
        ------
        UniverseException
            if the number of bots or layout width are odd
        LayoutEncodingException
            if there is something wrong with the layout_str, see `Layout()`

        """
        layout_chars = maze_components

        if number_bots % 2 != 0:
            raise UniverseException(
                "Number of bots in CTF must be even, is: %i"
                % number_bots)
        layout = Layout(layout_str, layout_chars, number_bots)
        layout_mesh = layout.as_mesh()
        initial_pos = extract_initial_positions(layout_mesh, number_bots)
        maze, food = create_maze(layout_mesh)
        if maze.width % 2 != 0:
            raise UniverseException(
                "Width of a layout for CTF must be even, is: %i"
                % maze.width)

        homezones = [
            (0, maze.width // 2 - 1),
            (maze.width // 2, maze.width - 1)
        ]

        teams = [Team(idx, homezone) for idx, homezone in enumerate(homezones)]

        bots = []
        for bot_index in range(number_bots):
            team_index = bot_index % 2
            bot = Bot(bot_index, initial_pos[bot_index],
                    team_index, homezones[team_index])
            bots.append(bot)

        return cls(maze, food, teams, bots)

    #: All possible (but not necessarily legal) moves
    _moves = [north, south, east, west, stop]

    #: the number of points to score when killing
    KILLPOINTS = 5

    def __init__(self, maze, food, teams, bots):
        self.maze = maze
        self.food = set(tuple(f) for f in food)
        self.teams = teams
        self.bots = bots

    @property
    def bot_positions(self):
        """ Current positions of all bots.

        Returns
        -------
        bot_positions : list of tuple of (int, int)
            the positions of all bots
        """
        return [bot.current_pos for bot in self.bots]

    @property
    def food_list(self):
        """ Positions of all the food.

        Returns
        -------
        food_positions : list of tuple of (int, int)
            the positions of all food

        """
        return self.food

    def team_food(self, team_index):
        """ Food that is owned by a team

        Returns
        -------
        team_food : list of tuple of (int, int)
            food owned by team

        """
        return [pos for pos in self.food_list
                if self.teams[team_index].in_zone(pos)]

    def enemy_food(self, team_index):
        """ Food that is edible by a team

        Returns
        -------
        team_food : list of tuple of (int, int)
            food edible by team

        """
        return [pos for pos in self.food_list
                if not self.teams[team_index].in_zone(pos)]

    def other_team_bots(self, bot_index):
        """ Obtain other bots on team.

        Parameters
        ----------
        bot_index : int
            index of the bot in question

        Returns
        -------
        other_team_bots : list of Bot objects
            the other bots on the team, excluding the desired bot

        """
        team_index = self.bots[bot_index].team_index
        return [bot for bot in self.team_bots(team_index)
                if not bot.index == bot_index]

    def team_bots(self, team_index):
        """ Obtain all Bot objects in a Team.

        Parameters
        ----------
        team_index : int
            the index of the desired team

        Returns
        -------
        team_bots : list of Bot objects

        """
        return [bot for bot in self.bots
                if bot.team_index == team_index]

    def enemy_bots(self, team_index):
        """ Obtain enemy bot objects.

        Parameters
        ----------
        team_index : int
            the index of the 'friendly' team

        Returns
        -------
        enemy_bots : list of Bot objects

        """
        return [bot for bot in self.bots
                if not bot.team_index == team_index]

    def enemy_team(self, team_index):
        """ Obtain the enemy team.

        Parameters
        ----------
        team_index : int
            the index of the 'friendly' team

        Returns
        -------
        enemy_team : Team object

        Raises
        ------
        UniverseException
            if there is more than one enemy team
        """
        other_teams = self.teams[:]
        other_teams.remove(self.teams[team_index])
        if len(other_teams) != 1:
            raise UniverseException("Expecting one enemy team. Found %i." % len(other_teams))
        return other_teams[0]

    def team_border(self, team_index):
        """ Positions of the border positions.

        These are the last positions in the zone of the team.

        Parameters
        ----------
        team_index : int
            the index of the 'friendly' team

        Returns
        -------
        team_border : list of tuple of (int, int)
            the border positions

        """
        x_min, x_max = 0, self.maze.shape[0]
        team_zone = self.teams[team_index].zone
        if team_zone[0] == x_min:
            border_x = team_zone[1]
        else:
            border_x = team_zone[0]
        return [(border_x, y) for y in range(self.maze.shape[1]) if not self.maze[border_x, y]]

    def move_bot(self, bot_id, move):
        """ Move a bot in certain direction.

        Parameters
        ----------
        bot_id : int
            index of the bot
        move : tuple of (int, int)
            direction to move in

        Returns
        -------
        game_state : dict
            the current game_state

        Raises
        ------
        IllegalMoveException
            if the move is invalid or impossible

        """
        # check legality of the move

        game_state = {}

        bot = self.bots[bot_id]
        legal_moves_dict = self.legal_moves(bot.current_pos)
        if move not in legal_moves_dict.keys():
            raise IllegalMoveException(
                'Illegal move from bot_id %r: %s' % (bot_id, move))
        old_pos = bot.current_pos
        new_pos = bot.current_pos = legal_moves_dict[move]

        game_state["bot_moved"] = [{"bot_id": bot_id, "old_pos": old_pos, "new_pos": new_pos}]

        team = self.teams[bot.team_index]
        # check for food being eaten
        game_state["food_eaten"] = []
        if bot.current_pos in self.food_list and not bot.in_own_zone:
            self.food.remove(bot.current_pos)

            game_state["food_eaten"] += [{"food_pos": bot.current_pos, "bot_id": bot_id}]

        # check for destruction
        game_state["bot_destroyed"] = []
        for enemy in self.enemy_bots(bot.team_index):
            if enemy.current_pos == bot.current_pos:
                if enemy.is_destroyer and bot.is_harvester:
                    destroyer = enemy.index
                    harvester = bot.index
                elif bot.is_destroyer and enemy.is_harvester:
                    destroyer = bot.index
                    harvester = enemy.index
                else:
                    continue

                # move on, if harvester is already destroyed
                if any(bot_destr["bot_id"]==harvester for bot_destr in game_state["bot_destroyed"]):
                    continue

                # otherwise mark for destruction
                game_state["bot_destroyed"] += [{'bot_id': harvester, 'destroyed_by': destroyer}]

        # reset bots
        for destroyed in game_state["bot_destroyed"]:
            old_pos = bot.current_pos
            self.bots[destroyed["bot_id"]]._to_initial()
            new_pos = bot.current_pos
            game_state["bot_moved"] += [{"bot_id": bot_id, "old_pos": old_pos, "new_pos": new_pos}]

        for food_eaten in game_state["food_eaten"]:
            self.teams[self.bots[food_eaten["bot_id"]].team_index].score += 1

        for bot_destroyed in game_state["bot_destroyed"]:
            self.teams[self.bots[bot_destroyed["destroyed_by"]].team_index].score += self.KILLPOINTS

        return game_state

        # TODO:
        # check for state change

    def legal_moves(self, position):
        """ Obtain legal moves and where they lead.

        Parameters
        ----------
        position : tuple of int (x, y)
            the position to start at

        Returns
        -------
        legal_moves_dict : dict mapping strings (moves) to positions (x, y)
            the legal moves and where they would lead.

        """
        legal_moves_dict = {}
        for move, new_pos in self.neighbourhood(position).items():
            try:
                if not self.maze[new_pos]:
                    legal_moves_dict[move] = new_pos
            except IndexError:
                # If we’re outside the maze, it is not a legal move.
                pass
        return legal_moves_dict

    def legal_moves_or_stop(self, position):
        """ Obtain legal moves (and where they lead)
        or just stop if impossible to move.

        Parameters
        ----------
        position : tuple of int (x, y)
            the position to start at

        Returns
        -------
        legal_moves : dict mapping strings (moves) to positions (x, y)
            the legal moves and where they would lead.
        """
        moves = self.legal_moves(position)

        if len(moves) > 1:
            del moves[stop]
        return moves

    def __repr__(self):
        return ("CTFUniverse(%r, %r, %r, %r)" %
            (self.maze, self.food, self.teams, self.bots))

    def __eq__(self, other):
        return type(self) == type(other) and self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not (self == other)

    @property
    def _char_mesh(self):
        char_mesh = Mesh(self.maze.width, self.maze.height)
        for pos in self.maze.positions:
            if self.maze[pos]:
                char_mesh[pos] = Wall
            elif pos in self.food:
                char_mesh[pos] = Food
            else:
                char_mesh[pos] = Free
        for bot in self.bots:
            # TODO what about bots on the same space?
            char_mesh[bot.current_pos] = str(bot.index)
        return char_mesh

    def __str__(self):
        return str(self._char_mesh)

    def copy(self):
        return self._from_json_dict(self._to_json_dict())

    @property
    def compact_str(self):
        return self._char_mesh.compact_str

    @property
    def pretty(self):
        """ Provide detailed, readable info about universe state.

        Returns
        -------
        pretty : str
            detailed, readable string version of this universe

        Examples
        --------
        >>> universe.pretty
        ##################
        #0#.  .  # .     #
        #1#####    #####2#
        #     . #  .  .#3#
        ##################
        Team(0, (0, 8), score=0)
            Bot(0, (1, 1), 0, (0, 8) , current_pos=(1, 1))
            Bot(2, (16, 2), 0, (0, 8) , current_pos=(16, 2))
        Team(1, (9, 17), score=0)
            Bot(1, (1, 2), 1, (9, 17) , current_pos=(1, 2))
            Bot(3, (16, 3), 1, (9, 17) , current_pos=(16, 3))

        """
        out = str()
        out += self.compact_str
        for team in self.teams:
            out += repr(team)
            out += '\n'
            for bot in self.team_bots(team.index):
                out += '\t' + repr(bot)
                out += '\n'
        return out

    def neighbourhood(self, position):
        """ Determine where a move will lead.

        Parameters
        ----------
        position : tuple of int (x, y)
            current position

        Returns
        -------
        new_pos : dict
            mapping of moves to new positions (x, y)

        """
        def iter_pos():
            for move in self._moves:
                pos = new_pos(position, move)
                if pos in self.maze:
                    yield move, pos
        return dict(iter_pos())

    def reachable(self, initial_positions):
        """ Returns all reachable positions starting from a list initial positions.

        Parameters
        ----------
        initial_positions : list(pos)
            list of initial positions

        Returns
        -------
        adjacency_list : generator of (pos, list(pos))
            Generator which contains all reachable positions and their adjacencies
        """
        return (it for it in iter_adjacencies(initial_positions, lambda pos: self.legal_moves(pos).values()))

    def free_positions(self):
        """ Returns an adjacency list for all Free positions.

        Returns
        -------
        adjacency_list : generator of (pos, list(pos))
            Generator which contains all reachable positions and their adjacencies
        """
        # Get the list of all free positions.
        free_pos = [pos for pos, val in self.maze.items() if not val]

        # Here we use a generator on a dictionary to create the adjacency list.
        # However, for Python 3, we force evaluation on the legal_moves.values
        return ((pos, list(self.legal_moves(pos).values())) for pos in free_pos)


    def _to_json_dict(self):
        return {"maze": self.maze._to_json_dict(),
                "food": list(self.food),
                "teams": [team._to_json_dict() for team in self.teams],
                "bots": [bot._to_json_dict() for bot in self.bots]}

    @classmethod
    def _from_json_dict(cls, item):
        return cls(maze=Maze._from_json_dict(item["maze"]),
                   food=item["food"],
                   teams=[Team._from_json_dict(team) for team in item["teams"]],
                   bots=[Bot._from_json_dict(bot) for bot in item["bots"]])
