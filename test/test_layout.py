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

def test_not_enclosed_by_walls():
    illegals = ("""# ###
                   #   #
                   #####""",
               """####
                     #
                  ####""",
              """####
                 #  #
                 ## #""")
    for illegal in illegals:
        with pytest.raises(ValueError):
            parse_single_layout(illegal)

def test_illegal_character():
    illegal_layout = (
        """ #######
            #    x#
            #a   c#
            #b    #
            ####### """)
    with pytest.raises(ValueError):
        out = parse_single_layout(illegal_layout)

def test_illegal_width():
    illegal_layout = (
        """ #####
            #   #
            #   #
            #   #
            ##### """)
    with pytest.raises(ValueError):
        out = parse_single_layout(illegal_layout)

def test_different_width():
    illegal_layout = (
        """ #######
            #      #
            #     #
            #     #
            ####### """)
    with pytest.raises(ValueError):
        out = parse_single_layout(illegal_layout)

def test_combined_layouts():
    layouts = """####
                 #  #
                 ####
                 ####
                 #  #
                 ####
                 ####
                 #  #
                 ####"""
    from_combined = parse_layout(layouts)
    from_single = parse_single_layout(layouts)
    assert from_combined == from_single

def test_combined_layouts_empty_lines():
    layouts = """
                 ####
                 #  #
                 ####

                 ####
                 #  #
                 ####

                 ####
                 #  #
                 ####"""
    from_combined = parse_layout(layouts)
    from_single = parse_single_layout(layouts)
    assert from_combined == from_single

def test_duplicate_bots_forbidden():
    layouts = """
                 ####
                 #aa#
                 ####
                 """
    with pytest.raises(ValueError):
        parse_layout(layouts)

@pytest.mark.xfail
def test_duplicate_bots_forbidden_multiple():
    layouts = """
                 ####
                 # a#
                 ####

                 ####
                 #a #
                 ####
                 """
    with pytest.raises(ValueError):
        parse_layout(layouts)

def test_duplicate_bots_allowed():
    layouts = """
                 ####
                 # x#
                 ####

                 ####
                 # x#
                 ####
                 """
    parsed_layout = parse_layout(layouts)
    assert parsed_layout['bots'][1] == (2, 1)

def test_combined_layouts_broken_lines():
    layouts = """
                 ####
                 #  #

                 ####
                 #  #
                 ####

                 ####
                 #  #
                 ####"""
    with pytest.raises(ValueError):
        from_combined = parse_layout(layouts)

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

def test_roundtrip_overlapping():
    input_layout =  """ ########
                        #a  .  #
                        #      #
                        #  .  y#
                        ########
                        ########
                        #b  .  #
                        #      #
                        #  .  x#
                        ########
                        ########
                        #.  .  #
                        #      #
                        #  .   #
                        ########"""

    expected_layout = \
"""########
#.  .  #
#      #
#  .   #
########
########
#a     #
#      #
#     x#
########
########
#b     #
#      #
#     y#
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
            #. #
            #### """)

    simple_layout_2 = (
        """

            ####
            #. #
            ####

            """)
    layout1 = parse_layout(simple_layout_1)
    layout2 = parse_layout(simple_layout_2)
    assert layout1 == layout2

def test_equal_positions():
    layout_str = """
        ########
        #a###  #
        # . ...#
        ########
        ########
        #b###  #
        # . ...#
        ########
        ########
        #x###  #
        # . ...#
        ########
        ########
        #y###  #
        # . ...#
        ########
    """
    layout = parse_layout(layout_str)
    assert layout['bots'] == [(1, 1)]*4


@pytest.mark.parametrize('pos, legal_positions', [
    ((2, 2), {(2, 1), (2, 3), (1, 2), (3, 2), (2, 2)}),
    ((1, 1), {(1, 2), (2, 1), (1, 1)}),
    ((4, 2), {(4, 2), (4, 1), (4, 3), (3, 2)}),
    ((4, 1), {(4, 2), (4, 1)})
])
def test_legal_positions(pos, legal_positions):
    test_layout = (
        """ ######
            #  # #
            #    #
            #    #
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
            #  # #
            #    #
            #    #
            ###### """)
    parsed = parse_layout(test_layout)
    with pytest.raises(ValueError):
        get_legal_positions(parsed['walls'], pos)


