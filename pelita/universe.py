from pelita.layout import Layout
from pelita.mesh import Mesh

__docformat__ = "restructuredtext"

wall   = '#'
food   = '.'
harvester = 'c'
destroyer = 'o'
free   = ' '

layout_chars = [wall, food, harvester, destroyer, free]

north = 'NORTH'
south = 'SOUTH'
west  = 'WEST'
east  = 'EAST'
stop  = 'STOP'

move_ids = [north, south, east, west, stop]

class Team(object):
    """ A team of bots.

    Attributes
    ----------
    index : int
        the index of the team within the Universe
    name : str
        the name of the team
    zone : tuple of int (x_min, x_max)
        the homezone of this team
    score : int
        the score of this team
    bots : list of int
        the bot indices that belong to this team

    Parameters
    ----------
    index : int
        the index of the team within the Universe
    index : int
        the index of the team within the Universe
    name : str
        the name of the team
    zone : tuple of int
        the homezone of this team
    score : int, optional, default = 0
        the score of this team
    bots : list of int, optional, default = None (creates an empty list)
        the bot indices that belong to this team

    """
    def __init__(self, index, name, zone, score=0, bots=None):
        self.index = index
        self.name = name
        self.zone = zone
        self.score = score
        # we can't use a keyword argument here, because that would create a
        # single list object for all our Teams.
        if not bots:
            self.bots = []
        else:
            self.bots = bots

    def _add_bot(self, bot):
        """ Add a bot to this team.

        Parameters
        ----------
        bot : int
            the index of the bot to add

        """
        self.bots.append(bot)

    def in_zone(self, position):
        """ Check if a position is within the zone

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

    def _score_point(self):
        """ Score a single point. """
        self.score += 1

    def __str__(self):
        return self.name

    def __repr__(self):
        return ('Team(%i, %r, %s, score=%i, bots=%r)' %
                (self.index, self.name, self.zone, self.score, self.bots))

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

class Bot(object):
    """ A bot on a team.

    Attributes
    ----------
    index : int
        the index of this bot within the Universe
    initial_pos : tuple of int (x, y)
        the initial position for this bot
    team_index : int
        the index of the team that this bot is on
    homezone : tuple of int (x_min, x_max)
        the homezone of this team
    current_pos : tuple of int (x, y)
        the current position of this bot
    in_own_zone : boolean, property
        True if in its own homezone and False otherwise
    is_destroyer : boolean
        True if a destroyer, False otherwise
    is_harvester : boolean, property
        not is_destroyer

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

    """
    def __init__(self, index, initial_pos, team_index, homezone,
            current_pos=None):
        self.index = index
        self.initial_pos = initial_pos
        self.team_index = team_index
        self.homezone = homezone
        if not current_pos:
            self.current_pos = self.initial_pos
        else:
            self.current_pos = current_pos
        if self.in_own_zone:
            self.is_destroyer = True
        else:
            self.is_destroyer = False

    @property
    def in_own_zone(self):
        return self.homezone[0] <= self.current_pos[0] <= self.homezone[1]

    @property
    def is_harvester(self):
        return not self.is_destroyer

    def _move(self, new_pos):
        """ Move this bot to a new location.

        Its state (harvester or destroyer) will be automatically updated.
        Whoever moves the bot is responsible for checking the legality of the
        new position.

        Parameters
        ----------
        new_pos : tuple of int (x, y)
            the new position for this bot
        """
        self.current_pos = new_pos
        if self.is_destroyer:
            if not self.in_own_zone:
                self.is_destroyer = False
        elif self.is_harvester:
            if self.in_own_zone:
                self.is_destroyer = True

    def _reset(self):
        """ Reset this bot to its initial position. """
        self._move(self.initial_pos)

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __cmp__(self, other):
        if self == other:
            return 0
        else:
            return self.index.__cmp__(other.index)

    def __repr__(self):
        return ('Bot(%i, %s, %i, %s , current_pos=%s)' %
                (self.index, self.initial_pos, self.team_index,
                    self.homezone, self.current_pos))


class MazeComponent(object):

    def __eq__(self, other):
        return isinstance(other, self.__class__)

class Free(MazeComponent):

    def __str__(self):
        return CTFUniverse.free

    def __repr__(self):
        return 'Free()'

class Wall(MazeComponent):

    def __str__(self):
        return CTFUniverse.wall

    def __repr__(self):
        return 'Wall()'

class Food(MazeComponent):
    def __str__(self):
        return CTFUniverse.food

    def __repr__(self):
        return 'Food()'

def create_maze(layout_mesh):
    """ Transforms a layout_mesh into a maze_mesh.

    Parameters
    ----------
    layout_mesh : Mesh of single char strings
        Mesh of single character strings describing the layout

    Returns
    -------
    maze_mesh : Mesh of lists
        Mesh of lists of MazeComponents

    """
    maze_mesh = Mesh(layout_mesh.width, layout_mesh.height,
            data=[[] for i in range(len(layout_mesh))])
    for index in maze_mesh.iterkeys():
        if layout_mesh[index] == CTFUniverse.wall:
            maze_mesh[index].append(Wall())
        else:
            maze_mesh[index].append(Free())
        if layout_mesh[index] == CTFUniverse.food:
            maze_mesh[index].append(Food())
    return maze_mesh

def create_CTFUniverse(layout_str, number_bots,
        team_names=['black', 'white']):

    if number_bots % 2 != 0:
        raise UniverseException(
            "Number of bots in CTF must be even, is: %i"
            % number_bots)
    layout = Layout(layout_str, layout_chars, number_bots)
    layout_mesh = layout.as_mesh()
    initial_pos = CTFUniverse.extract_initial_positions(layout_mesh, number_bots)
    maze_mesh = create_maze(layout_mesh)
    if maze_mesh.width % 2 != 0:
        raise UniverseException(
            "Width of a layout for CTF must be even, is: %i"
            % maze_mesh.width)
    homezones = [(0, maze_mesh.width//2-1), (maze_mesh.width//2,
        maze_mesh.width-1)]

    teams = []
    teams.append(Team(0, 'black', homezones[0], bots=range(0,
        number_bots, 2)))
    teams.append(Team(1, 'white', homezones[1], bots=range(1,
        number_bots, 2)))

    bots = []
    for bot_index in range(number_bots):
        team_index = bot_index%2
        bot =  Bot(bot_index, initial_pos[bot_index],
                team_index, homezones[team_index])
        bots.append(bot)

    return CTFUniverse(number_bots, layout, maze_mesh, teams, bots)

class UniverseException(Exception):
    pass

class IllegalMoveException(Exception):
    pass

class CTFUniverse(object):
    """ The Universe: representation of the game state.

    Attributes
    ----------
    number_bots : int
        total number of bots
    layout : Layout
        initial layout with food and agent positions
    maze_mesh : Mesh of single char strings
        static layout (free spaces and walls only)
    team_bots : dict of str to list of int
        the indices of the bots on each team
    team_score : dict of str to int
        the score of each team
    bots : lits of Bot objects
        all the bots in this universe
    food_mesh : Mesh of booleans
        the current food positions
    food_list : list of tuples, property
        indices of the remaining food

    Parameters
    ----------
    layout_str : str
        the layout for this universe
    number_bots : int
        the number of bots for this universe
    """

    wall   = '#'
    food   = '.'
    harvester = 'c'
    destroyer = 'o'
    free   = ' '

    layout_chars = [wall, food, harvester, destroyer, free]

    def __init__(self, number_bots, layout, maze_mesh, teams, bots):
        self.number_bots = number_bots
        self.layout = layout
        self.maze_mesh = maze_mesh
        self.teams = teams
        self.bots = bots

    @property
    def bot_positions(self):
        return [bot.current_pos for bot in self.bots]

    @property
    def food_list(self):
        return [key for (key, value) in self.maze_mesh.iteritems() if Food() in value]

    def move_bot(self, bot_id, move):
        # check legality of the move
        if move not in move_ids:
            raise IllegalMoveException(
                'Illegal move_id from bot %i: %s' % (bot_id, move))
        bot = self.bots[bot_id]
        legal_moves_dict = self.get_legal_moves(bot.current_pos)
        if move not in legal_moves_dict.keys():
            raise IllegalMoveException(
                'Illegal move from bot %r: %s'
                % (bot, move))
        bot._move(legal_moves_dict[move])
        # check for destruction
        other_teams = self.teams[:]
        other_teams.remove(self.teams[bot.team_index])
        other_team_bots = []
        for t in other_teams:
            other_team_bots.extend(t.bots)
        for enemy in [self.bots[i] for i in other_team_bots]:
            if enemy.current_pos == bot.current_pos:
                if enemy.is_destroyer and bot.is_harvester:
                    bot._reset()
                elif enemy.is_harvester and bot.is_destroyer:
                    enemy._reset()
        # check for food being eaten
        if Food() in self.maze_mesh[bot.current_pos]:
            self.maze_mesh[bot.current_pos].remove(Food())
            self.teams[bot.team_index]._score_point()

        # TODO:
        # check for state change
        # generate a list of events
        # propagate those events to observers
        # callbacks for the bots

    def get_legal_moves(self, position):
        legal_moves_dict = {}
        for move, new_pos in CTFUniverse.new_positions(position).items():
            if Free() in self.maze_mesh[new_pos]:
                legal_moves_dict[move] = new_pos
        return legal_moves_dict

    def __str__(self):
        # TODO what about bots on the same space?
        out = self.maze_mesh.copy()

        for (key, value) in self.maze_mesh.iteritems():
            if Wall() in value:
                out[key] = CTFUniverse.wall
            elif Food() in value:
                out[key] = CTFUniverse.food
            elif Free() in value:
                out[key] = CTFUniverse.free
        for bot in self.bots:
            out[bot.current_pos] = str(bot.index)
        return str(out)

    def as_str(self):
        output = str()
        for i in range(self.height):
            start = i * self.width
            end = start + self.width
            output += '['
            output += ', '.join((str(i) for i in  self._data[start:end]))
            output += ']'
            output += '\n'
        return output

    @staticmethod
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
        for k, v in mesh.iteritems():
            if v in bot_ids:
                start[int(v)] = k
                mesh[k] = CTFUniverse.free
        return start

    @staticmethod
    def new_positions(current):
        """ Determine where a move will lead.

        Parameters
        ----------
        current : int, int
            current position

        Returns
        -------
        new_pos : dict
            mapping of moves (str) to new_positions (int, int)

        """
        return {
            north : (current[0], current[1] - 1),
            south : (current[0], current[1] + 1),
            west  : (current[0] - 1, current[1]),
            east  : (current[0] + 1, current[1]),
            stop  : (current[0], current[1])}

    @staticmethod
    def is_adjacent(pos1, pos2):
        return (pos1[0] == pos2[0] and abs(pos1[1] - pos2[1]) == 1 or
            pos1[1] == pos2[1] and abs(pos1[0] - pos2[0]) == 1)
