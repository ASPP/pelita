from pathlib import Path
from textwrap import dedent
import pytest
from pelita.layout import *


def test_get_available_layouts():
    available = get_available_layouts(size='all')
    assert 300 == len(available)
    # now also test the filter
    available = get_available_layouts(size='normal')
    assert 100 == len(available)

def test_get_layout_by_name():
    target_layout = """
################
# ..       .. y#
#. ######..  #x#
#  .  .   .  # #
# #  .   .  .  #
#a#  ..###### .#
#b ..       .. #
################
"""
    loaded = get_layout_by_name('small_001')
    assert target_layout.strip() == loaded.strip()

def test_get_random_layout():
    fails = 0
    for i in range(10):
        l1 = get_random_layout()
        l2 = get_random_layout()
        if l1 == l2:
            fails += 1
    assert fails < 10, "Can't get random layouts!"

def test_get_random_layout_returns_correct_layout():
    name, layout = get_random_layout()
    layout2 = get_layout_by_name(name)
    assert layout == layout2

def test_get_random_layout_random_seed():
    name, layout = get_random_layout(size='small', seed=1)
    assert name == 'small_018'

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
    ewalls = []
    for x in range(6):
        for y in range(6):
            if (x == 0 or x == 5) or (y == 0 or y == 5):
                ewalls.append((x,y))
    ewalls.extend([(3, 2),(2, 3)])
    ewalls.sort()
    efood = sorted([(2, 1), (1, 2), (4, 3), (3, 4)])
    ebots = [(1, 3), (4, 2), (1, 4), (4, 1)]
    assert parsed_layout['walls'] == ewalls
    assert parsed_layout['food'] == efood
    assert parsed_layout['bots'] == ebots

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
    ewalls = []
    for x in range(6):
        for y in range(6):
            if (x == 0 or x == 5) or (y == 0 or y == 5):
                ewalls.append((x,y))
    ewalls.extend([(3, 2),(2, 3)])
    ewalls.sort()
    efood = sorted([(2, 1), (1, 2), (4, 3), (3, 4)]+added_food)
    ebots = [(1, 3), (4, 2), (1, 4), (4, 1)]
    assert parsed_layout['walls'] == ewalls
    assert parsed_layout['food'] == efood
    assert parsed_layout['bots'] == ebots

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
    with pytest.raises(ValueError, match=r"Missing bot\(s\): b"):
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
        parsed_layout = parse_layout(layout, food=added_food)
    added_food = [(2,3)]
    with pytest.raises(ValueError, match=r"food item at \(2, 3\) is .*"):
        parsed_layout = parse_layout(layout, food=added_food)

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
        parsed_layout = parse_layout(layout, bots=added_bots)
    added_bots = {'a':(2,3)}
    with pytest.raises(ValueError, match=r"bot a at \(2, 3\) is .*"):
        parsed_layout = parse_layout(layout, bots=added_bots)

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
        parsed_layout = parse_layout(layout, bots=added_bots)

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
    assert set(get_legal_positions(parsed['walls'], pos)) == legal_positions


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
        get_legal_positions(parsed['walls'], pos)


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
