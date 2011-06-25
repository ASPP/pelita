from pelita.layout import Layout
from pelita.mesh import Mesh

__docformat__ = "restructuredtext"


north = 'NORTH'
south = 'SOUTH'
west  = 'WEST'
east  = 'EAST'
stop  = 'STOP'

move_ids = [north, south, east, west, stop]

class Bot(object):

    def __init__(self, index, initial_pos, team, homezone,
            current_pos=None):
        self.index = index
        self.initial_pos = initial_pos
        self.team = team
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
        return self.homezone[0] <= self.current_pos[1] <= self.homezone[1]

    def move(self, new_pos):
        self.current_pos = new_pos
        if self.is_destroyer:
            if not self.in_own_zone:
                self.is_destroyer = False
        elif self.is_harvester:
            if self.in_own_zone:
                self.is_destroyer = True

    def reset(self):
        self.move(self.initial_pos)

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __cmp__(self, other):
        if self == other:
            return 0
        else:
            return self.index.__cmp__(other.index)

    def __repr__(self):
        return ('Bot(%i, %s, %r, %s ,current_pos=%s)' %
                (self.index, self.initial_pos, self.team,
                    self.homezone, self.current_pos))

    @property
    def is_harvester(self):
        return not self.is_destroyer

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

    def __init__(self, layout_str, number_bots):
        self.number_bots = number_bots
        if self.number_bots % 2 != 0:
            raise UniverseException(
                "Number of bots in CTF must be even, is: %i"
                % self.number_bots)
        self.layout = Layout(layout_str, CTFUniverse.layout_chars, number_bots)
        layout_mesh = self.layout.as_mesh()
        initial_pos = CTFUniverse.extract_initial_positions(layout_mesh, self.number_bots)
        self.maze_mesh = create_maze(layout_mesh)
        if self.maze_mesh.width % 2 != 0:
            raise UniverseException(
                "Width of a layout for CTF must be even, is: %i"
                % self.maze_mesh.width)

        team_names = ['black', 'white']

        self.team_bots = {team_names[0] : range(0, self.number_bots, 2),
                          team_names[1] : range(1, self.number_bots, 2)}
        self.team_score = {team_names[0] : 0, team_names[1] : 0}
        self.bots = []

        homezones = [(0, self.maze_mesh.width//2-1), (self.maze_mesh.width//2,
            self.maze_mesh.width-1)]
        for bot_index in range(self.number_bots):
                team_index = bot_index%2
                bot =  Bot(bot_index, initial_pos[bot_index],
                        team_names[team_index], homezones[team_index])
                self.bots.append(bot)

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
        bot.move(legal_moves_dict[move])
        # check for destruction
        other_team_names = [team for team in self.team_bots.keys() if not team == bot.team]
        other_team_bots = []
        for team_name in other_team_names:
            other_team_bots.extend(self.team_bots[team_name])
        for enemy in [self.bots[i] for i in other_team_bots]:
            if enemy.current_pos == bot.current_pos:
                if enemy.is_destroyer and bot.is_harvester:
                    bot.reset()
                elif enemy.is_harvester and bot.is_destroyer:
                    enemy.reset()
        # check for food being eaten
        if Food() in self.maze_mesh[bot.current_pos]:
            self.maze_mesh[bot.current_pos].remove(Food())
            self.team_score[bot.team] += 1

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
