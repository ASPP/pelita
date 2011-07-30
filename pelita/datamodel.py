# -*- coding: utf-8 -*-

""" The datamodel. """
import copy
from pelita.layout import Layout
from pelita.containers import Mesh, new_pos, TypeAwareList
from pelita.messaging.json_convert import serializable


__docformat__ = "restructuredtext"

north = (0, -1)
south = (0, 1)
west  = (-1, 0)
east  = (1, 0)
stop  = (0, 0)


@serializable
class Team(object):
    """ A team of bots.

    Parameters
    ----------
    index : int
        the index of the team within the Universe
    name : str
        the name of the team
    zone : tuple of int (x_min, x_max)
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

    def _to_json_dict(self):
        return {"index": self.index,
                "name": self.name,
                "zone": self.zone,
                "score": self.score,
                "bots": self.bots}

    @classmethod
    def _from_json_dict(cls, item):
        # need to convert the json list to a tuple
        item["zone"] = tuple(item["zone"])
        return cls(**item)

@serializable
class Bot(object):
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
    is_destroyer : boolean
        True if a destroyer, False otherwise
    is_harvester : boolean, property
        not is_destroyer

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

    def _to_json_dict(self):
        return {"index": self.index,
                "initial_pos": self.initial_pos,
                "team_index": self.team_index,
                "homezone": self.homezone,
                "current_pos": self.current_pos}

    @classmethod
    def _from_json_dict(cls, item):
        # need to convert the json list to a tuple
        for tupled_attr in ["initial_pos", "homezone", "current_pos"]:
            item[tupled_attr] = tuple(item[tupled_attr])
        return cls(**item)

class UniverseEvent(object):
    """ Base class for all events in a Universe. """

    def __eq__(self, other):
        return self.__dict__ == other.__dict__


class BotMoves(UniverseEvent):
    """ Signifies that a bot has moved.

    Parameters
    ----------
    bot_index : int
        index of the bot

    """
    def __init__(self, bot_index, old_pos, new_pos):
        self.bot_index = bot_index
        self.old_pos = old_pos
        self.new_pos = new_pos

    def __repr__(self):
        return ('BotMoves(%i, %r, %r)'
            % (self.bot_index, self.old_pos, self.new_pos))


class BotEats(UniverseEvent):
    """ Signifies that a bot has eaten food.

    Parameters
    ----------
    bot_index : int
        index of the bot

    """
    def __init__(self, bot_index, food_pos):
        self.bot_index = bot_index
        self.food_pos = food_pos

    def __repr__(self):
        return ('BotEats(%i, %r)'
            % (self.bot_index, self.food_pos))

class FoodEaten(UniverseEvent):
    """ Signifies that food has been eaten.

    Parameters
    ----------
    food_pos : tuple of (int, int)
        position of the eaten food

    """
    def __init__(self, food_pos):
        self.food_pos = food_pos

    def __repr__(self):
        return 'FoodEaten(%s)' % repr(self.food_pos)

class TeamScoreChange(UniverseEvent):
    """ Signifies that the score of a Team has changed.

    Parameters
    ----------
    team_index : int
        index of the team whos score has changed
    score_change : int
        the change in score
    new_score : int
        the new score
    """
    def __init__(self, team_index, score_change, new_score):
        self.team_index = team_index
        self.score_change = score_change
        self.new_score = new_score

    def __repr__(self):
        return ('TeamScoreChange(%i, %i, %i)' %
            (self.team_index, self.score_change, self.new_score))

class BotDestroyed(UniverseEvent):
    """ Signifies that a bot has been destroyed.

    Parameters
    ----------
    harvester_index : int
        index of the destroyed bot
    harvester_old_pos : tuple of (int, int)
        the position before moving
    harvester_new_pos : tuple of (int, int)
        the position after moving
    harvester_reset : tuple of (int, int)
        the reset position of the harvester
    destroyer_index : int
        index of the destroying bot
    destroyer_old_pos : tuple of (int, int)
        the position before moving
    destroyer_new_pos : tuple of (int, int)
        the position after moving

    """
    def __init__(self, harvester_index, harvester_old_pos,
            harvester_new_pos, harvester_reset,
            destroyer_index, destroyer_old_pos, destroyer_new_pos):
        self.harvester_index = harvester_index
        self.harvester_old_pos = harvester_old_pos
        self.harvester_new_pos = harvester_new_pos
        self.harvester_reset = harvester_reset
        self.destroyer_index = destroyer_index
        self.destroyer_old_pos = destroyer_old_pos
        self.destroyer_new_pos = destroyer_new_pos

    def __repr__(self):
        return ('BotDestroyed(%i, %r, %r, %r, %i, %r, %r)'
            % (self.harvester_index, self.harvester_old_pos,
                self.harvester_new_pos, self.harvester_reset,
                self.destroyer_index, self.destroyer_old_pos,
                self.destroyer_new_pos))


class TeamWins(UniverseEvent):
    """ Signify that a team has eaten all enemy food.

    Parameters
    ----------
    winning_team_index : int
        index of the winning team

    """
    def __init__(self, winning_team_index):
        self.winning_team_index = winning_team_index

    def __repr__(self):
        return ("TeamWins(%i)"
            % self.winning_team_index)

@serializable
class MazeComponent(object):
    """ Base class for all items inside a Maze. """

    def __str__(self):
        return self.__class__.char

    def __eq__(self, other):
        return isinstance(other, self.__class__)

    def _to_json_dict(self):
        return {}

    @classmethod
    def _from_json_dict(cls, item):
        return cls(**item)


@serializable
class Free(MazeComponent):
    """ Object to represent a free space. """

    char = ' '

    def __repr__(self):
        return 'Free()'

@serializable
class Wall(MazeComponent):
    """ Object to represent a wall. """

    char = '#'

    def __repr__(self):
        return 'Wall()'

@serializable
class Food(MazeComponent):
    """ Object to represent a food item. """

    char = '.'

    def __repr__(self):
        return 'Food()'


@serializable
class Maze(Mesh):
    """ A Mesh of TypeAwareLists of MazeComponents.

    This is a container class to represent a game maze. It is a two-dimensional
    structure (Mesh) which contains a special list (TypeAwareList) at each
    position. Further each TypeAwareList may contain only MazeComponent.

    """

    def __init__(self, width, height, data=None):
        if not data:
            data = [TypeAwareList(base_class=MazeComponent)
                    for i in range(width * height)]
        elif any([not isinstance(x, TypeAwareList) for x in data]):
            raise TypeError("Maze keyword argument 'data' should be list of"\
                    "TypeAwareList objects, not: %r" % data)
        super(Maze, self).__init__(width, height, data)

    def has_at(self, type_, pos):
        """ Check if objects of a given type are present at position.

        Parameters
        ----------
        type_ : type
            the type of objects to look for
        pos : tuple of (int, int)
            the position to look at

        Returns
        -------
        object_present : boolean
            True if objects of the given type are present and False otherwise.

        """
        return type_ in self[pos]

    def get_at(self, type_, pos):
        """ Get all objects of a given type at certain position.

        Parameters
        ----------
        type_ : type
            the type of objects to look for
        pos : tuple of (int, int)
            the position to look at

        Returns
        -------
        objs : list
            the objects at that position

        """
        return self[pos].filter_type(type_)

    def remove_at(self, type_, pos):
        """ Remove all objects of a given type at a certain position.

        Parameters
        ----------
        type_ : type
            the type of objects to look for
        pos : tuple of (int, int)
            the position to look at

        """
        self[pos].remove_type(type_)

    @property
    def positions(self):
        """ The indices of positions in the Maze.

        Returns
        -------
        positions : list of tuple of (int, int)
            the positions (x, y) in the Maze

        """
        return self.keys()

    def pos_of(self, type_):
        """ The indices of positions which have a MazeComponent. """
        return [pos for pos in self.positions if self.has_at(type_, pos)]


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
    for index in maze.iterkeys():
        if layout_mesh[index] == Wall.char:
            maze[index].append(Wall())
        else:
            maze[index].append(Free())
        if layout_mesh[index] == Food.char:
            maze[index].append(Food())
    return maze


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
            mesh[k] = Free.char
    return start


def create_CTFUniverse(layout_str, number_bots,
        team_names=['black', 'white']):
    """ Factory to create a 2-Player Capture The Flag Universe.

    Parameters
    ----------
    layout_str : str
        the string encoding the maze layout
    number_bots : int
        the number of bots in the game
    team_names : length 2 list of strings, optional default = ['black', 'white']
        the names of the playing teams

    Raises
    ------
    UniverseException
        if the number of bots or layout width are odd
    LayoutEncodingException
        if there is something wrong with the layout_str, see `Layout()`

    """
    layout_chars = [cls.char for cls in [Wall, Free, Food]]

    if number_bots % 2 != 0:
        raise UniverseException(
            "Number of bots in CTF must be even, is: %i"
            % number_bots)
    layout = Layout(layout_str, layout_chars, number_bots)
    layout_mesh = layout.as_mesh()
    initial_pos = extract_initial_positions(layout_mesh, number_bots)
    maze = create_maze(layout_mesh)
    if maze.width % 2 != 0:
        raise UniverseException(
            "Width of a layout for CTF must be even, is: %i"
            % maze.width)
    homezones = [(0, maze.width // 2 - 1),
            (maze.width // 2, maze.width - 1)]

    teams = []
    teams.append(Team(0, team_names[0], homezones[0], bots=range(0,
        number_bots, 2)))
    teams.append(Team(1, team_names[1], homezones[1], bots=range(1,
        number_bots, 2)))

    bots = []
    for bot_index in range(number_bots):
        team_index = bot_index % 2
        bot = Bot(bot_index, initial_pos[bot_index],
                team_index, homezones[team_index])
        bots.append(bot)

    return CTFUniverse(maze, teams, bots)


class UniverseException(Exception):
    """ Standard error in the Universe. """
    pass


class IllegalMoveException(Exception):
    """ Raised when a bot attempts to make an illegal move. """
    pass

@serializable
class CTFUniverse(object):
    """ The Universe: representation of the game state.

    Parameters
    ----------
    maze : mesh of lists of MazeComponent objects
        the maze
    teams : list of Team objects
        the teams
    bots : lits of Bot objects
        the bots

    Attributes
    ----------
    bot_positions : list of tuple of ints (x, y), property
        the current position of all bots
    food_list : list of typle of ints (x, y), property
        the positions of all edible food

    """

    move_ids = [north, south, east, west, stop]

    def __init__(self, maze, teams, bots):
        self.maze = maze
        # TODO make a deepcopy here, so that we can big_bang
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
        return self.maze.pos_of(Food)

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

    def team_bots(self, bot_index):
        """ Obtain other bots on team

        Parameters
        ----------
        bot_index : int
            index of the bot in question

        Returns
        -------
        team_bots : list of Bot objects
            the other bots on the team

        """
        team = self.teams[self.bots[bot_index].team_index]
        return [self.bots[i] for i in team.bots if i != bot_index]

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
        other_teams = self.teams[:]
        other_teams.remove(self.teams[team_index])
        other_team_bots = []
        for t in other_teams:
            other_team_bots.extend(t.bots)
        return [self.bots[i] for i in other_team_bots]

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
        events : list of UniverseEvent objects
            the events that happened during the move

        Raises
        ------
        IllegalMoveException
            if the string is an invalid or the move not possible

        """
        events = TypeAwareList(base_class=UniverseEvent)
        # check legality of the move
        if move not in self.move_ids:
            raise IllegalMoveException(
                'Illegal move_id from bot %i: %s' % (bot_id, move))
        bot = self.bots[bot_id]
        legal_moves_dict = self.get_legal_moves(bot.current_pos)
        if move not in legal_moves_dict.keys():
            raise IllegalMoveException(
                'Illegal move from bot %r: %s'
                % (bot, move))
        old_pos = bot.current_pos
        bot._move(legal_moves_dict[move])
        new_pos = bot.current_pos
        events.append(BotMoves(bot_id, old_pos, new_pos))
        # check for destruction
        for enemy in self.enemy_bots(bot.team_index):
            if enemy.current_pos == bot.current_pos:
                if enemy.is_destroyer and bot.is_harvester:
                    bot._reset()
                    events.append(BotDestroyed(
                        bot.index, old_pos, new_pos, bot.initial_pos,
                        enemy.index, enemy.current_pos, enemy.current_pos))
                elif enemy.is_harvester and bot.is_destroyer:
                    new_old_pos = enemy.current_pos
                    enemy._reset()
                    events.append(BotDestroyed(
                       enemy.index, new_old_pos, new_old_pos, enemy.initial_pos,
                       bot.index, old_pos, new_pos))
        # check for food being eaten
        if self.maze.has_at(Food, bot.current_pos) and not bot.in_own_zone:
            team = self.teams[bot.team_index]
            self.maze.remove_at(Food, bot.current_pos)
            team._score_point()
            events.append(BotEats(bot_id, bot.current_pos))
            events.append(FoodEaten(bot.current_pos))
            events.append(TeamScoreChange(team.index, 1, team.score))
            if not self.enemy_food(team.index):
                events.append(TeamWins(team.index))

        return events

        # TODO:
        # check for state change

    def get_legal_moves(self, position):
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
            if self.maze.has_at(Free, new_pos):
                legal_moves_dict[move] = new_pos
        return legal_moves_dict

    def __repr__(self):
        return ("CTFUniverse(%r, %r, %r)" %
            (self.maze, self.teams, self.bots))

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    @property
    def _char_mesh(self):
        char_mesh = Mesh(self.maze.width, self.maze.height)
        for pos in self.maze.positions:
            if self.maze.has_at(Wall, pos):
                char_mesh[pos] = Wall.char
            elif self.maze.has_at(Food, pos):
                char_mesh[pos] = Food.char
            elif self.maze.has_at(Free, pos):
                char_mesh[pos] = Free.char
        for bot in self.bots:
            # TODO what about bots on the same space?
            char_mesh[bot.current_pos] = str(bot.index)
        return char_mesh

    def __str__(self):
        return str(self._char_mesh)

    def copy(self):
        return copy.deepcopy(self)

    @property
    def compact_str(self):
        return self._char_mesh.compact_str

    @property
    def pretty(self):
        """ Provide detailed info about datamodel state.

        Returns
        -------
        pretty : str
            detailed, readable string version of this datamodel

        Examples
        --------
        >>> univere.pretty
        ##################
        #0#.  .  # .     #
        #1#####    #####2#
        #     . #  .  .#3#
        ##################
        Team(0, 'black', (0, 8), score=0, bots=[0, 2])
            Bot(0, (1, 1), 0, (0, 8) , current_pos=(1, 1))
            Bot(2, (16, 2), 0, (0, 8) , current_pos=(16, 2))
        Team(1, 'white', (9, 17), score=0, bots=[1, 3])
            Bot(1, (1, 2), 1, (9, 17) , current_pos=(1, 2))
            Bot(3, (16, 3), 1, (9, 17) , current_pos=(16, 3))

        """
        out = str()
        out += self.compact_str
        for team in self.teams:
            out += repr(team)
            out += '\n'
            for i in team.bots:
                out += '\t' + repr(self.bots[i])
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
        return dict([(move, new_pos(position, move)) for
            move in self.move_ids])

    @staticmethod
    def is_adjacent(pos1, pos2):
        return (pos1[0] == pos2[0] and abs(pos1[1] - pos2[1]) == 1 or
            pos1[1] == pos2[1] and abs(pos1[0] - pos2[0]) == 1)

    def _to_json_dict(self):
        return {"maze": self.maze,
                "teams": self.teams,
                "bots": self.bots}

    @classmethod
    def _from_json_dict(cls, item):
        return cls(**item)

