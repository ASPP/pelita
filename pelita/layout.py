
import io

# bot to index conversion
BOT_N2I = {'a': 0, 'b': 2, 'x': 1, 'y': 3}
BOT_I2N = {0: 'a', 2: 'b', 1: 'x', 3: 'y'}


def parse_layout(layout_str, food=None, bots=None, strict=True):
    """Parse a layout string.

    If strict is False, the layout string must not be valid and parse_layout will
    try its best to interpret it. This is useful only during testing.

    A valid layout string is enclosed by walls and rectangular:

     ########
     #a  .  #
     #b ## x#
     #  .  y#
     ########


    Return a dict
        {'walls': sorted tuple of wall coordinates,
         'food' : list of food coordinates,
         'bots'  : list of bot coordinates in the order [a, x, b, y],
         'shape': tuple of (height, width) of the layout}

    In the example above:
    {'walls': ((0, 0), (0, 1), (0, 2), (0, 3), (0, 4), (1, 0), (1, 4), (2, 0),
               (2, 4), (3, 0), (3, 2), (3, 4), (4, 0), (4, 2), (4, 4), (5, 0),
               (5, 4), (6, 0), (6, 4), (7, 0), (7, 1), (7, 2), (7, 3), (7, 4)),
     'food': [(3, 3), (4, 1)],
     'bots': [(1, 1), (6, 2), (1, 2), (6, 3)],
     'shape': (8, 4)}

    Additional food and bots can be passed:

      - food: a list of coordinates of additional food pellets
      - bots: a dictionary { char : (coord_x, coord_y)}, where char in 'a', 'b', 'x', 'y'
              bots specified this way override the coordinates of bots found in the string
    """

    if bots is None:
        bots = {}
    if food is None:
        food = []

    # set empty default values
    lwalls = set()
    lfood = []
    lbots = [None] * 4

    width = None
    # list of layout rows
    rows = []
    start = False
    for i, line in enumerate(layout_str.splitlines()):
        row = line.strip()
        if not row:
            # always ignore empty lines
            continue
        # a layout is always started by a full row of walls
        if not start:
            if row.count('#') != len(row):
                raise ValueError(f"Layout must be enclosed by walls (line: {i})!")
            else:
                # start the layout parsing
                start = True
                # set width of layout
                width = len(row)
                # check that width is even
                if width % 2 and strict:
                    raise ValueError(f"Layout width must be even (found {width})!")
                rows.append(row)
                continue
        # Here we are within the layout
        # every row must have the same length
        if len(row) != width:
            raise ValueError(f"Layout rows have differing widths (line: {i})!")
        # rows are always enclosed by walls
        if row[0] != '#' or row[-1] != '#':
            raise ValueError(f"Layout must be enclosed by walls (line:{i})!")
        # append current row to the list of rows
        rows.append(row)
        # detect closing row and ignore whatever follows
        if row.count('#') == len(row):
            start = False
            break

    if start:
        # layout has not been closed!
        raise ValueError(f"Layout must be enclosed by walls (line:{i})!")

    # height of the layout (y-axis)
    height = len(rows)

    # iterate through the grid of characters
    for y, row in enumerate(rows):
        for x, char in enumerate(row):
            coord = (x, y)
            # assign the char to the corresponding list
            if char == '#':
                # wall
                lwalls.add(coord)
            elif char == '.':
                # food
                lfood.append(coord)
            elif char == ' ':
                # empty
                continue
            elif char in BOT_N2I.keys():
                # legal bots
                bot_idx = BOT_N2I[char]
                if lbots[bot_idx] is not None:
                    # bot_idx has already been set before
                    raise ValueError(f"Cannot set bot {BOT_I2N[bot_idx]} to {coord} (already at {lbots[bot_idx]}).")
                lbots[bot_idx] = coord
            else:
                raise ValueError(f"Unknown character {char} in maze at {coord}!")
    missing_bots = []
    for i, bot in enumerate(lbots):
        if bot is None and BOT_I2N[i] not in bots:
            missing_bots.append(BOT_I2N[i])
    if missing_bots and strict:
            raise ValueError(f"Missing bot(s): {missing_bots}")
    lfood.sort()

    # if additional food was supplied, we add it
    for c in food:
        if not ((0 <= c[0] < width) and (0 <= c[1] < height)):
            raise ValueError(f"food item at {c} is outside of maze!")
        elif c in lwalls:
            raise ValueError(f"food item at {c} is on a wall!")
        else:
            lfood = sorted(list(set(food + lfood)))

    if not (set(bots.keys()) <= set(BOT_N2I.keys())):
        raise ValueError(f"Invalid Bot names in {bots}.")

    # check if additional bots are on legal positions
    for bn, bpos in bots.items():
        if not ((0 <= bpos[0] < width) and (0 <= bpos[1] < height)):
            raise ValueError(f"bot {bn} at {bpos} is outside of maze!")
        elif bpos in lwalls:
            raise ValueError(f"bot {bn} at {bpos} is on a wall!")
        else:
            # override bots
            lbots[BOT_N2I[bn]] = bpos

    # build parsed layout, ensuring walls and food are sorted
    parsed_layout = {
        'walls': tuple(sorted(lwalls)),
        'food': sorted(lfood),
        'bots': lbots,
        'shape': (width, height)
    }

    return parsed_layout


def layout_as_str(*, walls, food=None, bots=None, shape=None):
    """Given a dictionary with walls, food and bots coordinates return a string layout representation

    Example:

    Given:
    {'walls': [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4), (1, 0), (1, 4), (2, 0),
               (2, 4), (3, 0), (3, 2), (3, 4), (4, 0), (4, 2), (4, 4), (5, 0),
               (5, 4), (6, 0), (6, 4), (7, 0), (7, 1), (7, 2), (7, 3), (7, 4)],
     'food': [(3, 3), (4, 1)],
     'bots': [(1, 1), (6, 2), (1, 2), (6, 3)],
     'shape': (8, 4)}

    Return:
    ########
    #a  .  #
    #b ## x#
    #  .  y#
    ########

    Overlapping items are discarded. When overlapping, walls take precedence over
    bots, which take precedence over food.

    The shape is optional. When it does not match the borders of the maze, a ValueError
    is raised.
    """
    # make walls a set for faster access
    walls = set(walls)
    width, height = wall_dimensions(walls)

    if shape is not None and not (width, height) == shape:
        raise ValueError(f"Given shape {shape} does not match width and height of layout {(width, height)}.")

    # initialized empty containers
    if food is None:
        food = set()
    else:
        food = set(food)

    if bots is None:
        bots = []

    out = io.StringIO()
    for y in range(height):
        for x in range(width):
            out_char = " "
            if (x, y) in walls:
                # always print walls
                out_char = '#'
            elif (x, y) in bots:
                # Bot has the next priority
                bot_ix = bots.index((x,y))
                out_char = BOT_I2N[bot_ix]
            elif (x, y) in food:
                out_char = '.'
             # close the row
            out.write(out_char)
        out.write('\n')
    return out.getvalue()


def wall_dimensions(walls):
    """ Given a list of walls, returns the shape of the maze as a tuple of (width, height)"""
    max_elem = max(walls)
    width = max_elem[0] + 1
    height = max_elem[1] + 1
    return (width, height)


def initial_positions(walls, shape):
    """Calculate initial positions.

    Given the list of walls, returns the free positions that are closest to the
    bottom left and top right corner. The algorithm starts searching from
    (1, height-2) and (width-2, 1) respectively and uses the Manhattan distance
    for judging what is closest. On equal distances, a smaller distance in the
    x value is preferred.
    """
    width, height = shape

    left_start = (1, height - 2)
    left = []
    right_start = (width - 2, 1)
    right = []

    dist = 0
    while len(left) < 2:
        # iterate through all possible x distances (inclusive)
        for x_dist in range(dist + 1):
            y_dist = dist - x_dist
            pos = (left_start[0] + x_dist, left_start[1] - y_dist)
            # if both coordinates are out of bounds, we stop
            if not (0 <= pos[0] < width) and not (0 <= pos[1] < height):
                raise ValueError("Not enough free initial positions.")
            # if one coordinate is out of bounds, we just continue
            if not (0 <= pos[0] < width) or not (0 <= pos[1] < height):
                continue
            # check if the new value is free
            if pos not in walls:
                left.append(pos)

            if len(left) == 2:
                break

        dist += 1

    dist = 0
    while len(right) < 2:
        # iterate through all possible x distances (inclusive)
        for x_dist in range(dist + 1):
            y_dist = dist - x_dist
            pos = (right_start[0] - x_dist, right_start[1] + y_dist)
            # if both coordinates are out of bounds, we stop
            if not (0 <= pos[0] < width) and not (0 <= pos[1] < height):
                raise ValueError("Not enough free initial positions.")
            # if one coordinate is out of bounds, we just continue
            if not (0 <= pos[0] < width) or not (0 <= pos[1] < height):
                continue
            # check if the new value is free
            if pos not in walls:
                right.append(pos)

            if len(right) == 2:
                break

        dist += 1

    # lower indices start further away
    left.reverse()
    right.reverse()
    return [left[0], right[0], left[1], right[1]]


def get_legal_positions(walls, shape, bot_position):
    """ Returns all legal positions that a bot at `bot_position`
    can go to.

     Parameters
    ----------
    walls : set of (int, int)
        position of the walls of current layout.
    bot_position: tuple
        position of current bot.

    Returns
    -------
    list
        legal positions

    Raises
    ------
    ValueError
        if bot_position invalid or on wall
    """
    width, height = shape
    if not (0, 0) <= bot_position < (width, height):
        raise ValueError(f"Position {bot_position} not inside maze ({width}x{height}).")
    if bot_position in walls:
        raise ValueError(f"Position {bot_position} is on a wall.")
    north = (0, -1)
    south = (0, 1)
    east = (1, 0)
    west = (-1, 0)
    stop = (0, 0)
    directions = [north, east, west, south, stop]
    potential_moves = [(i[0] + bot_position[0], i[1] + bot_position[1]) for i in directions]
    possible_moves = [i for i in potential_moves if i not in walls]
    return possible_moves
