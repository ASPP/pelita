from functools import reduce
from io import StringIO
import random

from ..game_master import GameMaster
from ..containers import Mesh
from ..datamodel import Maze
from ..player.team import Team, create_homezones, Game, Bot


def stopping(turn, game):
    return (0, 0)

def setup_test_game(*, layout, game=None, is_blue=True, rounds=None, score=None, seed=None):
    if game is not None:
        raise RuntimeError("Re-using an old game is not implemented yet.")

    if isinstance(layout, str):
        layout = create_layout(layout)
#    elif not isinstance(layout, Layout):
#        raise TypeError("layout needs to be of type Layout or str.")

    walls = [pos for pos, is_wall in layout.walls.items() if is_wall]
    width = max(walls)[0] + 1
    height = max(walls)[1] + 1

    total_food = layout.food
    num_bots = 4
    bots = []
    for bot_index in range(num_bots):
        team_index = bot_index % 2

        position = None
        initial_position = None
        is_noisy = False

        if team_index == 0:
            homezone = create_homezones(width, height)[0]
        else:
            homezone = create_homezones(width, height)[1]

        if score is None:
            score = [0, 0]

        team_food = [f for f in total_food if f in homezone]

        rng = random.Random(seed)

        bot = Bot(
            bot_index=bot_index,
            position=position,
            initial_position=initial_position,
            walls=walls,
            homezone=homezone,
            food=team_food,
            is_noisy=is_noisy,
            score=score[team_index],
            random=rng,
            round=round,
            is_blue=is_blue)

        bots.append(bot)

    for bot in bots:
        bot._bots = bots

    if is_blue:
        team = [bots[0], bots[2]]
        enemy = [bots[1], bots[3]]
    else:
        team = [bots[1], bots[3]]
        enemy = [bots[0], bots[2]]

    team[0].position = layout.bot_positions["0"]
    team[1].position = layout.bot_positions["1"]

    enemy[0].position = layout.bot_positions["E"][0]
    enemy[1].position = layout.bot_positions["E"][1]

    team[0]._initial_position = layout.initial_positions[0 if is_blue else 1][0]
    team[1]._initial_position = layout.initial_positions[0 if is_blue else 1][1]

    enemy[0]._initial_position = layout.initial_positions[1 if is_blue else 0][0]
    enemy[1]._initial_position = layout.initial_positions[1 if is_blue else 0][1]

    storage = {}

    game = Game(team, storage)
    return game

# TODO: Print maze from bot

# @dataclass
class Layout:
    def __init__(self, walls, food, bot_positions):
        self.walls = walls
        self.food = food
        self.bot_positions = bot_positions
        self.initial_positions = self.guess_initial_positions(self.walls)

    def guess_initial_positions(self, walls):
        """ Returns the free positions that are closest to the bottom left and
        top right corner. The algorithm starts searching from (1, -2) and (-2, 1)
        respectively and uses the manhattan distance for judging what is closest.
        On equal distances, a smaller distance in the x value is preferred.
        """
        left_start = (1, walls.height - 2)
        left_initials = []
        right_start = (walls.width - 2, 1)
        right_initials = []

        dist = 0
        while len(left_initials) < 2:
            # iterate through all possible x distances (inclusive)
            for x_dist in range(dist + 1):
                y_dist = dist - x_dist
                pos = (left_start[0] + x_dist, left_start[1] - y_dist)
                # if both coordinates are out of bounds, we stop
                if not (0 <= pos[0] < walls.width) and not (0 <= pos[1] < walls.height):
                    raise ValueError("Not enough free initial positions.")
                # if one coordinate is out of bounds, we just continue
                if not (0 <= pos[0] < walls.width) or not (0 <= pos[1] < walls.height):
                    continue
                # check if the new value is free
                if not walls[pos]:
                    left_initials.append(pos)

                if len(left_initials) == 2:
                    break

            dist += 1

        dist = 0
        while len(right_initials) < 2:
            # iterate through all possible x distances (inclusive)
            for x_dist in range(dist + 1):
                y_dist = dist - x_dist
                pos = (right_start[0] - x_dist, right_start[1] + y_dist)
                # if both coordinates are out of bounds, we stop
                if not (0 <= pos[0] < walls.width) and not (0 <= pos[1] < walls.height):
                    raise ValueError("Not enough free initial positions.")
                # if one coordinate is out of bounds, we just continue
                if not (0 <= pos[0] < walls.width) or not (0 <= pos[1] < walls.height):
                    continue
                # check if the new value is free
                if not walls[pos]:
                    right_initials.append(pos)

                if len(right_initials) == 2:
                    break

            dist += 1

        # lower indices start further away
        left_initials.reverse()
        right_initials.reverse()
        return left_initials, right_initials


    def merge(self, other):
        if not self.walls:
            self.walls = other.walls
        if self.walls != other.walls:
            raise ValueError("Walls are not equal.")

        self.food += other.food
        # remove duplicates
        self.food = list(set(self.food))

        if not self.bot_positions:
            self.bot_positions = other.bot_positions

        for bot, pos in other.bot_positions.items():
            if bot not in self.bot_positions:
                self.bot_positions[bot] = pos
            elif self.bot_positions[bot] != pos:
                raise ValueError("Bot %s has already been defined" % bot)
            else:
                pass
                # nothing to do, we have it already
        # return our merged self
        return self

    def _repr_html_(self):
        walls = self.walls
        with StringIO() as out:
            out.write("<table>")
            for y in range(walls.height):
                out.write("<tr>")
                for x in range(walls.width):
                    if walls[x, y]:
                        bg = 'style="background-color: {}"'.format(
                            "rgb(94, 158, 217)" if x < walls.width // 2 else
                            "rgb(235, 90, 90)")
                    elif (x, y) in self.initial_positions[0]:
                        bg = 'style="background-color: #ffffcc"'
                    elif (x, y) in self.initial_positions[1]:
                        bg = 'style="background-color: #ffffcc"'
                    else:
                        bg = ""
                    out.write("<td %s>" % bg)
                    if walls[x, y]: out.write("#")
                    if (x, y) in self.food: out.write('<span style="color: rgb(247, 150, 213)">●</span>')
                    for bot, pos in self.bot_positions.items():
                        if bot == "E":
                            for p in pos:
                                if p == (x, y):
                                    out.write(str(bot))
                        else:
                            if pos == (x, y):
                                out.write(str(bot))
                    out.write("</td>")
                out.write("</tr>")
            out.write("</table>")
            return out.getvalue()

    def __str__(self):
        walls = self.walls
        with StringIO() as out:
            out.write('\n')
            # first, print walls and food
            for y in range(walls.height):
                for x in range(walls.width):
                    if walls[x, y]: out.write('#')
                    elif (x, y ) in self.food: out.write('.')
                    else: out.write(' ')
                out.write('\n')
            out.write('\n')
            # print walls and bots

            # reverse the mapping in bot_positions
            bots = {}
            for bot, pos in self.bot_positions.items():
                if bot == "E":
                    for p in pos:
                        bots[p] = 'E'
                else:
                    bots[pos] = bot

            for y in range(walls.height):
                for x in range(walls.width):
                    if walls[x, y]: out.write('#')
                    elif (x, y) in bots: out.write(bots[(x, y)])
                    else: out.write(' ')
                out.write('\n')
            out.write('\n')
            return out.getvalue()


    def __eq__(self, other):
        return ((self.walls, self.food, self.bot_positions, self.initial_positions) ==
                (other.walls, other.food, other.bot_positions, other.initial_positions))


def create_layout(*layout_strings, food=None, teams=None, enemy=None):
    # layout_strings can be a list of strings or one huge string
    # with many layouts after another
    layouts = [
        load_layout(layout)
        for layout_str in layout_strings
        for layout in split_layout_str(layout_str)
    ]
    return reduce(lambda x, y: x.merge(y), layouts)

def split_layout_str(layout_str):
    """ Turns a layout string containing many layouts into a list
    of simple layouts.
    """
    out = []
    current_layout = []
    for row in layout_str.splitlines():
        stripped = row.strip()
        if not stripped:
            # found an empty line
            # if we have a current_layout, append it to out
            # and reset it
            if current_layout:
                out.append(current_layout)
                current_layout = []
            continue
        # non-empty line: append to current_layout
        current_layout.append(row)

    return ['\n'.join(l) for l in out]

def load_layout(layout_str):
    build = []
    width = None
    height = None

    food = []
    bots = {}

    for row in layout_str.splitlines():
        stripped = row.strip()
        if not stripped:
            continue
        if width is not None:
            if len(stripped) != width:
                raise ValueError("Layout has differing widths.")
        width = len(stripped)
        build.append(stripped)

    height = len(build)
    mesh = Mesh(width, height, data=list("".join(build)))
    # Check that the layout is surrounded with walls
    for i in range(width):
        if not (mesh[i, 0] == mesh[i, height - 1] == '#'):
            raise ValueError("Layout not surrounded with #.")
    for j in range(height):
        if not (mesh[0, j] == mesh[width - 1, j] == '#'):
            raise ValueError("Layout not surrounded with #.")

    walls = Maze(mesh.width, mesh.height)
    # extract the non-wall values from mesh
    for idx, val in mesh.items():
        # We know that each val is only one character, so it is
        # either wall or something else
        if '#' in val:
            walls[idx] = True
        # free: skip
        elif ' ' in val:
            continue
        # food
        elif '.' in val:
            food.append(idx)
        # other
        else:
            if 'E' in val:
                # We can have several undefined enemies
                bots[val] = [*bots.get(val, []), idx]
            else:
                bots[val] = idx

    # If we have only one enemy defined, we duplicate it.
    if 'E' in bots and len(bots['E']) == 1:
        bots['E'].append(bots['E'][0])

    return Layout(walls, food, bots)
