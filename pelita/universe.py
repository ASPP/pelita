from pelita.layout import Layout
from pelita.mesh import Mesh

__docformat__ = "restructuredtext"


north = 'NORTH'
south = 'SOUTH'
west  = 'WEST'
east  = 'EAST'
stop  = 'STOP'

move_ids = [north, south, east, west, stop]

class Team(object):

    def __init__(self, name, zone, score=0, bots=None):
        self.name = name
        self.zone = zone
        self.score = score
        # we can't use a keyword argument here, because that would create a
        # single list object for all our Teams.
        if not bots:
            self.bots = []
        else:
            self.bots = bots


    def add_bot(self, bot):
        self.bots.append(bot)

    def in_zone(self, position):
        return self.zone[0] <= position[0] <= self.zone[1]

    def score_point(self):
        self.score += 1

    def __repr__(self):
        return ('Team(%r, %s, score=%i, bots=%r)' %
                (self.name, self.zone, self.score, self.bots))

    def __eq__(self, other):
        return self.__dict__ == other.__dict__


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
        self.current_pos = self.initial_pos

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __cmp__(self, other):
        if self == other:
            return 0
        else:
            return self.index.__cmp__(other.index)

    def __repr__(self):
        return ('Bot(%i, %s, %s, destroyer=%r, current_position=%s)' %
                (self.index, self.initial_pos, self.team.name,
                self.is_destroyer, self.current_pos))

    @property
    def is_harvester(self):
        return not self.is_destroyer


class UniverseException(Exception):
    pass

class IllegalMoveException(Exception):
    pass

class CTFUniverse(object):
    """ The Universe: representation of the game state.

    Attributes
    ----------
    red_team : list of int
        bot indices of the read team (left)
    blue_team : list of int
        bot indices of the blue team (left)
    layout : Layout
        initial layout with food and agent positions
    number_bots : int
        total number of bots
    mesh : Mesh of single char strings
        static layout (free spaces and walls only)
    red_zone: tuple of int
        beginning and end index of the red zone (width)
    blue_zone: tuple of int
        beginning and end index of the blue zone (width)
    initial_pos : list of (int, int)
        the initial positions for the bots
    bot_positions : list of (int, int)
        the current positions of the bots
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
        self.mesh = self.layout.as_mesh()
        if self.mesh.width % 2 != 0:
            raise UniverseException(
                "Width of a layout for CTF must be even, is: %i"
                % self.mesh.width)

        self.teams = []
        self.bots = []
        self.teams.append(Team('red', (0, self.mesh.width//2-1)))
        self.teams.append(Team('blue', (self.mesh.width//2, self.mesh.width-1)))

        homezones = [(0, self.mesh.width//2-1), (self.mesh.width//2, self.mesh.width-1)]
        initial_pos = CTFUniverse.extract_initial_positions(self.mesh, self.number_bots)
        for bot_index in range(self.number_bots):
                team_index = bot_index%2
                bot =  Bot(bot_index, initial_pos[bot_index],
                        self.teams[team_index].name, homezones[team_index])
                self.teams[team_index].add_bot(bot)
                self.bots.append(bot)
        self.food_mesh = CTFUniverse.extract_food_mesh(self.mesh)

    @property
    def bot_positions(self):
        return [bot.current_pos for bot in self.bots]

    @property
    def food_list(self):
        return [key for (key, value) in self.food_mesh.iteritems() if value]

    def score(self, bot_index):
        if self.on_red_team(bot_index):
            self.red_score += 1
        elif self.on_blue_team(bot_index):
            self.blue_score += 1

    def move_bot(self, bot_id, move):
        # check legality of the move
        if move not in move_ids:
            raise IllegalMoveException(
                'Illegal move_id from bot %i: %s' % (bot_id, move))
        bot = self.bots[bot_id]
        legal_moves_dict = self.get_legal_moves(bot.current_pos)
        if move not in legal_moves_dict.keys():
            raise IllegalMoveException(
                'Illegal move from bot %i at %s: %s'
                % (bot_id, str(bot.current_pos), move))
        bot.move(legal_moves_dict[move])
        # check for destruction
        other_teams = self.teams[:]
        other_teams = [t for t in self.teams if not t.name == bot.team]
        my_team = [t for t in self.teams if t.name == bot.team][0]
        for enemy in other_teams[0].bots:
            if enemy.current_pos == bot.current_pos:
                if enemy.is_destroyer and bot.is_harvester:
                    bot.reset()
                elif enemy.is_harvester and bot.is_destroyer:
                    enemy.reset()
        # check for food being eaten
        if self.food_mesh[bot.current_pos]:
            self.food_mesh[bot.current_pos] = False
            my_team.score_point()

        # TODO:
        # check for state change
        # generate a list of events
        # propagate those events to observers
        # callbacks for the bots

    def get_legal_moves(self, position):
        legal_moves_dict = {}
        for move, new_pos in CTFUniverse.new_positions(position).items():
            if self.mesh[new_pos] == CTFUniverse.free:
                legal_moves_dict[move] = new_pos
        return legal_moves_dict

    def __str__(self):
        # TODO what about bots on the same space?
        out = self.mesh.copy()
        for i in range(self.number_bots):
            out[self.bot_positions[i]] = str(i)
        for food_index in self.food_list:
            out[food_index] = CTFUniverse.food
        return str(out)

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
    def extract_food_mesh(mesh):
        """ Extract positions of food in the mesh.

        Also replaces the food positions in the mesh with free spaces.

        Parameters
        ----------
        mesh : Mesh of characters
            the layout in mesh format

        Returns
        -------
        food_mesh : Mesh of booleans

        """
        food_mesh = Mesh(*mesh.shape)
        for k, v in mesh.iteritems():
            if v == CTFUniverse.food:
                food_mesh[k] = True
                mesh[k] = CTFUniverse.free
            else:
                food_mesh[k] = False
        return food_mesh

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
