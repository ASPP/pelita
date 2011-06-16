wall   = '#'
food   = '.'
harvester = 'c'
destroyer = 'o'

layout_chars = [wall, food, harvester, destroyer]

north = 'NORTH'
south = 'SOUTH'
west  = 'WEST'
east  = 'EAST'

class LayoutEncodingException(Exception):
    pass

def check_layout(layout_str, number_bots):
    """ Check the legality of the layout string.

    Parameters
    ----------
    layout_str : str
        the layout string
    number_bots : int
        the total number of bots that should be present

    Raises
    ------
    LayoutEncodingException
        if an illegal character is encountered
    LayoutEncodingException
        if a bot-id is missing
    LayoutEncodingException
        if a bot-id is specified twice

    """
    bot_ids = [str(i) for i in range(1, number_bots+1)]
    existing_bots = []
    legal = layout_chars + bot_ids  + [' ', '\n']
    for c in layout_str:
        if c not in legal:
            raise LayoutEncodingException(
                "Char: '%c' is not a legal layout character" % c)
        if c in bot_ids:
            if c in existing_bots:
                raise LayoutEncodingException(
                    "Bot-ID: '%c' was specified twice" % c)
            else:
                existing_bots.append(c)
    if bot_ids != existing_bots:
        missing = [str(i) for i in set(bot_ids).difference(set(existing_bots))]
        missing.sort()
        raise LayoutEncodingException(
            'Layout is invalid for %i Bots, The following IDs were missing: %s '
            % (number_bots, missing))
    lines = layout_str.split('\n')
    for i in range(len(lines)):
        if len(lines[i]) != len(lines[0]):
            raise LayoutEncodingException(
                'The layout must be rectangular,'+\
                'line %i has length %i instead of %i'
                % (i, len(lines[i]), len(lines[0])))

def strip_layout(layout_str):
    """ Remove whitespace from a string encoded layout

    Parameters
    ----------
    layout_str : str
        the layout, possibly with whitespace

    Returns
    -------
    layout_str : str
        the layout with whitespace removed

    """
    return ''.join([line.strip()+'\n' for line in layout_str.split('\n')])

class Universe(object):

    def __init__():
        pass

    def init_bots():
        pass

    def get_number_bots():
        pass

    def move_bot(index, move):
        pass

    def reset_bot(index):
        pass

if __name__ == "__main__":
    test_layout = """#######
                     #c    #
                     #  .  #
                     #    o#
                     #######"""
    print strip_layout(test_layout)

    illeagal_layout = """#######
                         #c    #
                         #  f  #
                         #    o#
                         #######"""
    try:
        check_layout(strip_layout(illeagal_layout), 0)
    except Exception, e:
        print e

    not_enough_bots = """#######
                         #1    #
                         #  2  #
                         #    3#
                         #######"""
    try:
        check_layout(strip_layout(not_enough_bots), 5)
    except Exception, e:
        print e

    too_many_bots = """#######
                       #1    #
                       #  1  #
                       #    3#
                       #######"""
    try:
        check_layout(strip_layout(too_many_bots), 3)
    except Exception, e:
        print e

    wrong_shape = """#######
                     #  #
                     #   #
                     #    #
                     ######"""
    try:
        check_layout(strip_layout(wrong_shape), 0)
    except Exception, e:
        print e
