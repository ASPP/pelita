import base64
import io
import random
import zlib

try:
    from . import __layouts
except SyntaxError as err:
    print("Invalid syntax in __layouts module. Pelita will not be able to use built-in layouts.")
    print(err)

class Layout:
    pass

class LayoutEncodingException(Exception):
    """ Signifies a problem with the encoding of a layout. """
    pass

def load_layout(layout_name=None, layout_file=None):
    """ Returns the layout_name and layout_string for a given parameter.

    The Parameters 'layout_name' and 'layout_file' are mutually exclusive.

    Parameters
    ----------
    layout_name : string, optional
        The name of an available layout
    layout_file : filename, optional
        A file which holds a layout

    Returns
    -------
    layout : tuple(str, str)
        the name of the layout, a random layout string
    """
    if layout_name and not layout_file:
        layout_name = layout_name
        layout_string = get_layout_by_name(layout_name)
    elif layout_file and not layout_name:
        with open(layout_file) as file:
            layout_name = file.name
            layout_string = file.read()
    else:
        raise  ValueError("Can only supply one of: 'layout_name' or 'layout_file'")

    return layout_name, layout_string

def get_random_layout(filter=''):
    """ Return a random layout string from the available ones.

    Parameters
    ----------
    filter : str
        only return layouts which contain "filter" in their name.
        Default is no filter.

    Returns
    -------
    layout : tuple(str, str)
        the name of the layout, a random layout string

    Examples
    --------
    To only get layouts without dead ends you may use:

        >>> get_random_layout(filter='without_dead_ends')

    """
    layouts_names = [item for item in get_available_layouts() if filter in item]
    layout_choice = random.choice(layouts_names)
    return layout_choice, get_layout_by_name(layout_choice)

def get_available_layouts(filter=''):
    """ The names of the available layouts.

    Parameters
    ----------
    filter : str
        only return layouts which contain 'filter' in their name.
        Default is no filter.

    Returns
    -------
    layout_names : list of str
        the available layouts

    Examples
    --------
    To only get layouts without dead ends you may use:

        >>> get_available_layouts(filter='without_dead_ends')

    """
    # loop in layouts dictionary and look for layout strings
    return [item for item in dir(__layouts) if item.startswith('layout_') and
            filter in item]

def get_layout_by_name(layout_name):
    """ Get a layout.

    Parameters
    ----------
    layout_name : str
        a valid layout name

    Returns
    -------
    layout_str : str
        the layout as a string

    Raises
    ------
    KeyError
        if the layout_name is not known

    See Also
    --------
    get_available_layouts
    """
    # decode and return this layout
    try:
        return zlib.decompress(base64.decodebytes(__layouts.__dict__[layout_name].encode())).decode()
    except KeyError as ke:
        # This happens if layout_name is not a valid key in the __dict__.
        # I.e. if the layout_name is not available.
        # The error message would be to terse "KeyError: 'non_existing_layout'",
        # thus reraise as ValueError with appropriate error message.
        raise ValueError("Layout: '%s' is not known." % ke.args)

def parse_layout(layout_str):
    """Parse a layout string

    Return a dict
        {'walls': list_of_wall_coordinates,
         'food' : list_of_food_coordinates,
         'bot'  : list_of_4_bot_coordinate}

    A layout string is composed of wall characters '#', food characters '.', and
    bot characters '0', '1', '2', and '3'.

    Valid layouts must be enclosed by walls and be of rectangular shape. Example:

     ########
     #0  .  #
     #2    1#
     #  .  3#
     ########


    If items are overlapping, several layout strings can be concateneted:
     ########
     #0  .  #
     #     1#
     #  .  3#
     ########
     ########
     #2  .  #
     #     1#
     #  .  3#
     ########

     In this case, bot '0' and bot '2' are on top of each other at position (1,1)
    """
    layout_list = []
    start = False
    for i, line in enumerate(layout_str.splitlines()):
        row = line.strip()
        if not row:
            # ignore emptylines
            continue
        if not start:
            # start a new layout
            current_layout = [row]
            start = True
            continue
        # we are in the middle of a layout, just append to the current
        # layout unless we detect the closing string
        current_layout.append(row)
        if row.count('#') == len(row):
            # this is a closing string
            # append the layout to tha layout list
            layout_list.append('\n'.join(current_layout))
            start = False

    if start:
        # the last layout has not been closed, close it here
        layout_list.append('\n'.join(current_layout))

    # initialize walls, food and bots from the first layout
    out = parse_single_layout(layout_list.pop(0))
    for layout in layout_list:
        items = parse_layout(layout)
        # walls should always be the same
        if items['walls'] != out['walls']:
            raise ValueError('Walls are not equal in all layouts!')
        # add the food, removing duplicates
        out['food'] = list(set(out['food'] + items['food']))
        # add the bots
        for bot_idx, bot_pos in enumerate(items['bots']):
            if bot_pos:
                # this bot position is not None, overwrite whatever we had before
                out['bots'][bot_idx] = bot_pos

    return out

def parse_single_layout(layout_str):
    """Parse a single layout from a string

    See parse_layout for details about valid layout strings.
    """
    # width of the layout (x-axis)
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
                if width % 2:
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
    walls = []
    food = []
    # bot positions (we assume 4 bots)
    bots = [None]*4

    # iterate through the grid of characters
    for y, row in enumerate(rows):
        for x, char in enumerate(row):
            coord = (x, y)
            # assign the char to the corresponding list
            if char == '#':
                # wall
                walls.append(coord)
            elif char == '.':
                # food
                food.append(coord)
            elif char == ' ':
                # empty
                continue
            else:
                # bot
                try:
                    # we expect an 0<=index<=3
                    bot_idx = int(char)
                    if bot_idx >= len(bots):
                        # reuse the except below
                        raise ValueError
                except ValueError:
                    raise ValueError(f"Unknown character {char} in maze!")
                bots[bot_idx] = coord
    walls.sort()
    food.sort()
    return {'walls':walls, 'food':food, 'bots':bots}

def layout_as_str(*, walls, food=None, bots=None):
    """Given walls, food and bots return a string layout representation

    Returns a combined layout string.

    The first layout string contains walls and food, the subsequent layout
    strings contain walls and bots. If bots are overlapping, as many layout
    strings are appended as there are overlapping bots.

    Example:

    ####
    #  #
    ####
    """
    walls = sorted(walls)
    width = max(walls)[0] + 1
    height = max(walls)[1] + 1


    # flag to check if we have overlapping objects

    # when need_combined is True, we force the printing of a combined layout
    # string:
    # - the first layout will have walls and food
    # - subsequent layouts will have walls and bots
    # You'll get as many layouts as you have overlapping bots
    need_combined = False

    # first, check if we have overlapping bots
    if len(set(bots)) != len(bots):
        need_combined = True
    else:
        need_combined = any(coord in food for coord in bots)
    # then, check that bots are not overlapping with food

    with io.StringIO() as out:
        for y in range(height):
            for x in range(width):
                if (x, y) in walls:
                    # always print walls
                    out.write('#')
                elif (x, y) in food:
                    # always print food
                    out.write('.')
                else:
                    if not need_combined:
                        # check if we have a bot here only when we know that
                        # we won't need a combined layout later
                        if (x, y) in bots:
                            out.write(str(bots.index((x, y))))
                        else:
                            out.write(' ')
                    else:
                        out.write(' ')
            # close the row
            out.write('\n')

        # return here if we don't need a combined layout string
        if not need_combined:
            return out.getvalue()

        # create a mapping coordinate : list of bots at this coordinate
        coord_bots = {}
        for idx, pos in enumerate(bots):
            if pos is None:
                # if a bot coordinate is None
                # don't put the bot in the layout
                continue
            # append bot_index to the list of bots at this coordinate
            # if still no bot was seen here we have to start with an empty list
            coord_bots[pos] = coord_bots.get(pos, []) + [str(idx)]

        # loop through the bot coordinates
        while coord_bots:
            for y in range(height):
                for x in range(width):
                    # let's repeat the walls
                    if (x, y) in walls:
                        out.write('#')
                    elif (x, y) in coord_bots:
                        # get the first bot at this position and remove it
                        # from the list
                        bot_idx = coord_bots[(x, y)].pop(0)
                        out.write(bot_idx)
                        # if we are left without bots at this position
                        # remove the coordinate from the dict
                        if not coord_bots[(x, y)]:
                            del coord_bots[(x, y)]
                    else:
                        # empty space
                        out.write(' ')
                # close the row
                out.write('\n')

        # drop the last empty line: we always have two at the end
        return out.getvalue()


