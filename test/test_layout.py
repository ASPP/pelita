import itertools
from textwrap import dedent

import pytest

from pelita.layout import (BOT_N2I, get_legal_positions, layout_as_str,
                           parse_layout, wall_dimensions)


def test_legal_layout():
    layout = """
             ######
             # . y#
             #. #x#
             #a# .#
             #b . #
             ######
             """
    parsed_layout = parse_layout(layout)
    ewalls = set()
    for x in range(6):
        for y in range(6):
            if (x == 0 or x == 5) or (y == 0 or y == 5):
                ewalls.add((x,y))
    ewalls.update([(3, 2),(2, 3)])
    efood = sorted([(2, 1), (1, 2), (4, 3), (3, 4)])
    ebots = [(1, 3), (4, 2), (1, 4), (4, 1)]
    assert parsed_layout['walls'] == tuple(sorted(ewalls))
    assert parsed_layout['food'] == efood
    assert parsed_layout['bots'] == ebots
    assert parsed_layout['shape'] == (6, 6)
    assert wall_dimensions(parsed_layout['walls']) == parsed_layout['shape']

def test_legal_layout_with_added_items():
    layout = """
             ######
             # . y#
             #. #x#
             #a# .#
             #  . #
             ######
             """
    added_food = [(1,1), (4,4)]
    added_bots = {'b': (1,4)}
    parsed_layout = parse_layout(layout, food=added_food, bots=added_bots)
    ewalls = set()
    for x in range(6):
        for y in range(6):
            if (x == 0 or x == 5) or (y == 0 or y == 5):
                ewalls.add((x,y))
    ewalls.update([(3, 2),(2, 3)])
    efood = sorted([(2, 1), (1, 2), (4, 3), (3, 4)]+added_food)
    ebots = [(1, 3), (4, 2), (1, 4), (4, 1)]
    assert parsed_layout['walls'] == tuple(sorted(ewalls))
    assert parsed_layout['food'] == efood
    assert parsed_layout['bots'] == ebots
    assert parsed_layout['shape'] == (6, 6)
    assert wall_dimensions(parsed_layout['walls']) == parsed_layout['shape']

def test_hole_in_horizontal_border():
    layout = """
             ###### #########
             # ..       .. y#
             #. ######..  #x#
             #  .  .   .  # #
             # #  .   .  .  #
             #a#  ..###### .#
             #b ..       .. #
             ################
             """
    with pytest.raises(ValueError, match=r"Layout must be enclosed by walls.*"):
        parse_layout(layout)

def test_odd_width():
    layout = """
             ###############
             #  .      .. y#
             #. #####..  #x#
             #  .     .  # #
             # #  .  .  .  #
             #a#  .###### .#
             #b ..      .. #
             ###############
             """
    with pytest.raises(ValueError, match=r"Layout width must be even.*"):
        parse_layout(layout)

def test_different_widths():
    layout = """
             ################
             # ..        .. y#
             #. ######..  #x#
             #  .  .   .  # #
             # #  .   .  .  #
             #a#  ..###### .#
             #b ..       .. #
             ################
             """
    with pytest.raises(ValueError, match=r"Layout rows have differing widths.*"):
        parse_layout(layout)

def test_hole_in_vertical_border():
    layout = """
             ################
             # ..       .. y#
             #. ######..  # #
             #  .  .   .  # x
             # #  .   .  .  #
             #a#  ..###### .#
             #b ..       .. #
             ################
             """
    with pytest.raises(ValueError, match=r"Layout must be enclosed by walls.*"):
        parse_layout(layout)

def test_last_row_not_complete():
    layout = """
             ################
             # ..       .. y#
             #. ######..  #x#
             #  .  .   .  # #
             # #  .   .  .  #
             #a#  ..###### .#
             #b ..       .. #
             """
    with pytest.raises(ValueError, match=r"Layout must be enclosed by walls.*"):
        parse_layout(layout)

def test_twice_the_same_bot():
    layout = """
             ################
             # ..       .. y#
             #. ######..  #y#
             #  .  .   .  # #
             # #  .   .  .  #
             #a#  ..###### .#
             #b ..       .. #
             ################
             """
    with pytest.raises(ValueError, match=r"Cannot set bot y to \(14, 2\) .*"):
        parse_layout(layout)

def test_missing_one_bot():
    layout = """
             ################
             # ..       .. y#
             #. ######..  #x#
             #  .  .   .  # #
             # #  .   .  .  #
             #a#  ..###### .#
             #  ..       .. #
             ################
             """
    with pytest.raises(ValueError, match=r".* ['b']"):
        parse_layout(layout)

def test_broken_added_food():
    layout = """
             ######
             # . y#
             #. #x#
             #a# .#
             #b . #
             ######
             """
    added_food = [(10,10)]
    with pytest.raises(ValueError, match=r"food item at \(10, 10\) is .*"):
        parse_layout(layout, food=added_food)
    added_food = [(2,3)]
    with pytest.raises(ValueError, match=r"food item at \(2, 3\) is .*"):
        parse_layout(layout, food=added_food)

def test_broken_added_bot():
    layout = """
             ######
             # . y#
             #. #x#
             # # .#
             #b . #
             ######
             """
    added_bots = {'a': (10,10)}
    with pytest.raises(ValueError, match=r"bot a at \(10, 10\) is .*"):
        parse_layout(layout, bots=added_bots)
    added_bots = {'a':(2,3)}
    with pytest.raises(ValueError, match=r"bot a at \(2, 3\) is .*"):
        parse_layout(layout, bots=added_bots)

def test_override_bot():
    layout = """
             ######
             # . y#
             #. #x#
             #a# .#
             #b . #
             ######
             """
    added_bots = {'a': (1,1)}
    parsed_layout = parse_layout(layout, bots=added_bots)
    assert parsed_layout['bots'][0] == (1,1)

def test_wrong_bot_names():
    layout = """
             ######
             # . y#
             #. #x#
             #a# .#
             #b . #
             ######
             """
    added_bots = {'e': (1,1)}
    with pytest.raises(ValueError, match=r"Invalid Bot names in .*"):
        parse_layout(layout, bots=added_bots)

def test_wrong_bot_names_2():
    layout = """
             ######
             # . e#
             #. #x#
             #a# .#
             #b . #
             ######
             """
    added_bots = {'y': (1,1)}
    with pytest.raises(ValueError, match=r"Unknown character.*"):
        parse_layout(layout, bots=added_bots)

def test_roundtrip():
    input_layout =  """ ########
                        #a  .  #
                        #b    x#
                        #  .  y#
                        ########
                        """

    expected_layout = \
"""########
#a  .  #
#b    x#
#  .  y#
########
"""
    layout = parse_layout(input_layout)
    out = layout_as_str(**layout)
    assert out == dedent(expected_layout)
    layout = parse_layout(out)
    out = layout_as_str(**layout)
    assert out == dedent(expected_layout)


def test_incomplete_roundtrip():
    # We create a layout where a, b and x, y sit on top of each other and on a food pellet.
    input_layout =  """ ########
                        #b  .  #
                        #      #
                        #  .  x#
                        ########
                        """
    ab_bots = (1, 1)
    xy_bots = (6, 3)
    bots = {'a': ab_bots, 'b': ab_bots, 'x': xy_bots, 'y': xy_bots }
    food = [ab_bots, xy_bots]

    # In the layout_as_str, a and x will be shown but nothing else
    expected_layout = \
"""########
#a  .  #
#      #
#  .  x#
########
"""
    layout = parse_layout(input_layout, bots=bots, food=food)
    out = layout_as_str(**layout)
    assert out == dedent(expected_layout)

def test_layout_as_str():
    input_layout =  """ ########
                        #a #.  #
                        #b    x#
                        #  .# y#
                        ########
                        """
    layout = parse_layout(input_layout)

    expected_layout = """
        ########
        #  #   #
        #      #
        #   #  #
        ########
        """
    out = layout_as_str(walls=layout['walls'])
    assert out.strip() == dedent(expected_layout).strip()

    expected_layout = """
        ########
        #  #.  #
        #      #
        #  .#  #
        ########
        """
    out = layout_as_str(walls=layout['walls'], food=layout['food'])
    assert out.strip() == dedent(expected_layout).strip()

    expected_layout = """
        ########
        #a #   #
        #b    x#
        #   # y#
        ########
        """
    out = layout_as_str(walls=layout['walls'], bots=layout['bots'])
    assert out.strip() == dedent(expected_layout).strip()

    expected_layout = """
        ########
        #a #.  #
        #b    x#
        #  .# y#
        ########
        """
    out = layout_as_str(walls=layout['walls'], food=layout['food'], bots=layout['bots'])
    assert out.strip() == dedent(expected_layout).strip()

    with pytest.raises(TypeError):
        # no walls
        layout_as_str(food=layout['food'], bots=layout['bots'], shape=(1, 1))

    with pytest.raises(ValueError):
        # bad shape
        layout_as_str(walls=layout['walls'], food=layout['food'], bots=layout['bots'], shape=(1, 1))


def test_empty_lines():
    simple_layout_1 = (
        """ ####
            #ax#
            #by#
            #. #
        #### """)

    simple_layout_2 = (
        """

            ####
            #ax#
            #by#
            #. #
            ####

            """)
    layout1 = parse_layout(simple_layout_1)
    layout2 = parse_layout(simple_layout_2)
    assert layout1 == layout2


@pytest.mark.parametrize('pos, legal_positions', [
    ((2, 2), {(2, 1), (2, 3), (1, 2), (3, 2), (2, 2)}),
    ((1, 1), {(1, 2), (2, 1), (1, 1)}),
    ((4, 2), {(4, 2), (4, 1), (4, 3), (3, 2)}),
    ((4, 1), {(4, 2), (4, 1)})
])
def test_legal_positions(pos, legal_positions):
    test_layout = (
        """ ######
            #a # #
            #b   #
            #xy  #
            ###### """)
    parsed = parse_layout(test_layout)
    assert set(get_legal_positions(parsed['walls'], parsed['shape'], pos)) == legal_positions


@pytest.mark.parametrize('pos', [
    (0, 0),
    (0, 1),
    (-1, 0),
    (7, 7),
    (3, 1)
])
def test_legal_positions_fail(pos):
    test_layout = (
        """ ######
            #a # #
            #b   #
            #yx  #
            ###### """)
    parsed = parse_layout(test_layout)
    with pytest.raises(ValueError):
        get_legal_positions(parsed['walls'], parsed['shape'], pos)


def test_load():
    layout1="""
        ########
        # ###ya#
        #bx ...#
        ########
    """
    layout = parse_layout(layout1)
    assert layout['bots'] == [(6, 1), (2, 2), (1, 2),(5, 1)]

def test_bots_in_same_position():
    layout_str = """
        ########
        # ###  #
        # . ...#
        ########
    """
    bot_dict = {"a": (1, 1),
                "b": (1, 1),
                "x": (1, 1),
                "y": (1, 1)}
    layout = parse_layout(layout_str, bots=bot_dict)
    assert layout['bots'] == [(1, 1), (1, 1), (1, 1),(1, 1)]


# All combinations of bots that can be switched on/off
@pytest.mark.parametrize('bots_hidden', itertools.product(*[(True, False)] * 4))
def test_parse_layout_game_bad_number_of_bots(bots_hidden):
    """ parse_layout should fail when a wrong number of bots is given. """
    test_layout = """
        ##################
        #a#.  .  # .     #
        #b#####    #####y#
        #     . #  .  .#x#
        ################## """
    # remove bot i when bots_hidden[i] is True
    for char, idx in BOT_N2I.items():
        if bots_hidden[idx]:
            test_layout = test_layout.replace(char, ' ')

    if list(bots_hidden) == [False] * 4:
        # no bots are hidden. it should succeed
        parsed_layout = parse_layout(test_layout)
        assert parsed_layout['bots'] == [(1, 1), (16, 3), (1, 2), (16, 2)]
    else:
        with pytest.raises(ValueError):
            parse_layout(test_layout)
