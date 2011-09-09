import unittest
from pelita.containers import Mesh
from pelita.datamodel import Wall, Free, Food
from pelita.layout import *

class TestLayoutModule(unittest.TestCase):

    def test_get_available_layouts(self):
        target = ['layout_01_demo',
                  'layout_01_with_dead_ends',
                  'layout_01_without_dead_ends',
                  'layout_02_demo',
                  'layout_02_with_dead_ends',
                  'layout_02_without_dead_ends',
                  'layout_03_demo',
                  'layout_03_with_dead_ends',
                  'layout_03_without_dead_ends',
                  'layout_04_demo',
                  'layout_04_with_dead_ends',
                  'layout_04_without_dead_ends',
                  'layout_05_with_dead_ends',
                  'layout_05_without_dead_ends',
                  'layout_06_with_dead_ends',
                  'layout_06_without_dead_ends',
                  'layout_07_with_dead_ends',
                  'layout_07_without_dead_ends',
                  'layout_08_with_dead_ends',
                  'layout_08_without_dead_ends',
                  'layout_09_with_dead_ends',
                  'layout_09_without_dead_ends',
                  'layout_10_with_dead_ends',
                  'layout_10_without_dead_ends',
                  'layout_11_with_dead_ends',
                  'layout_11_without_dead_ends',
                  'layout_12_with_dead_ends',
                  'layout_12_without_dead_ends',
                  'layout_13_with_dead_ends',
                  'layout_13_without_dead_ends',
                  'layout_14_with_dead_ends',
                  'layout_14_without_dead_ends',
                  'layout_15_with_dead_ends',
                  'layout_15_without_dead_ends',
                  'layout_16_with_dead_ends',
                  'layout_16_without_dead_ends',
                  'layout_17_with_dead_ends',
                  'layout_17_without_dead_ends',
                  'layout_18_with_dead_ends',
                  'layout_18_without_dead_ends',
                  'layout_19_with_dead_ends',
                  'layout_19_without_dead_ends',
                  'layout_20_with_dead_ends',
                  'layout_20_without_dead_ends',
                  'layout_office']
        available = get_available_layouts()
        self.assertEqual(target, available)

    def test_get_layout_by_name(self):
        # sorry about the indentation, but this is exactly how the string is
        target_layout = ("""################################
#   #. #.#.#       #     #.#.#3#
# # ##       ##  #   ###   #.#1#
# # #. # ###    #### .#..# # # #
# # ## # ..# #   #   ##### # # #
# #    ##### ###   ###.#   # # #
# ## # ..#.  #.###       #   # #
# #. ##.####        #.####  ## #
# ##  ####.#        ####.## .# #
# #   #       ###.#  .#.. # ## #
# # #   #.###   ### #####    # #
# # # #####   #   # #.. # ## # #
# # # #..#. ####    ### # .# # #
#0#.#   ###   #  ##       ## # #
#2#.#.#     #       #.#.# .#   #
################################
""")
        print target_layout
        loaded = get_layout_by_name('layout_01_demo')
        print loaded
        self.assertEqual(target_layout, loaded)

    def test_get_random_layout(self):
        available = get_available_layouts()
        random1 = get_random_layout()
        random2 = get_random_layout()
        self.assertNotEqual(random1, random2,
                'Testing randomized function, may fail sometimes.')


class TestLayoutChecks(unittest.TestCase):

    layout_chars = [Wall.char, Free.char, Food.char]

    def test_strip_layout(self):
        test_layout = (
            """ #######
                #c    #
                #  .  #
                #    o#
                ####### """)
        stripped = [c for c in Layout.strip_layout(test_layout)]
        target = ['#', '#', '#', '#', '#', '#', '#', '\n',
                  '#', 'c', ' ', ' ', ' ', ' ', '#', '\n',
                  '#', ' ', ' ', '.', ' ', ' ', '#', '\n',
                  '#', ' ', ' ', ' ', ' ', 'o', '#', '\n',
                  '#', '#', '#', '#', '#', '#', '#']
        self.assertEqual(stripped, target)

    def test_illegal_character(self):
        illegal_layout = (
            """ #######
                #c    #
                #  f  #
                #    o#
                ####### """)
        self.assertRaises(LayoutEncodingException, Layout.check_layout,
                Layout.strip_layout(illegal_layout),
                TestLayoutChecks.layout_chars, 0)

    def test_not_enough_bots(self):
        not_enough_bots = (
            """ #######
                #0    #
                #  1  #
                #    2#
                ####### """)
        self.assertRaises(LayoutEncodingException, Layout.check_layout,
                Layout.strip_layout(not_enough_bots),
                TestLayoutChecks.layout_chars, 5)

    def test_too_many_bots(self):
        too_many_bots = (
            """ #######
                #0    #
                #  0  #
                #    2#
                ####### """)
        self.assertRaises(LayoutEncodingException, Layout.check_layout,
                Layout.strip_layout(too_many_bots),
                TestLayoutChecks.layout_chars, 3)

    def test_wrong_shape(self):
        wrong_shape = (
            """ #######
                #  #
                #   #
                #    #
                ######  """)
        self.assertRaises(LayoutEncodingException, Layout.check_layout,
                Layout.strip_layout(wrong_shape),
                TestLayoutChecks.layout_chars, 0)

    def test_layout_shape(self):
        small_shape = (
            """ ###
                # #
                ### """)
        self.assertEqual(Layout.layout_shape(Layout.strip_layout(small_shape)), (3, 3))

        large_shape = (
            """ #######
                #     #
                #     #
                #     #
                ####### """)
        self.assertEqual(Layout.layout_shape(Layout.strip_layout(large_shape)), (7, 5))

    def test_wrong_bot_order(self):
        unordered = (
            """ #######
                #3    #
                #2 0  #
                #    1#
                ####### """)
        # this should not raise an exception, unfortunately there isn't such a
        # thing in unittest
        l = Layout(unordered,
                TestLayoutChecks.layout_chars, 4)

    def test_str(self):
        simple_layout = (
            """ ####
                #. #
                #### """)
        layout = Layout(simple_layout, TestLayoutChecks.layout_chars, 0)
        target = '####\n'+\
                 '#. #\n'+\
                 '####'
        self.assertEqual(target, str(layout))

    def test_eq(self):
        eq_test = (
            """ ########
                #0  .  #
                #2    1#
                #  .  3#
                ######## """)
        layout = Layout(eq_test, TestLayoutChecks.layout_chars, 4)
        layout2 = Layout(eq_test, TestLayoutChecks.layout_chars, 4)
        self.assertEqual(layout, layout2)
        neq_test = (
            """ ######
                #0   #
                #    #
                #   1#
                ###### """)
        layout3 = Layout(neq_test, TestLayoutChecks.layout_chars, 2)
        self.assertNotEqual(layout, layout3)

    def test_repr(self):
        repr_test = (
            """ ########
                #0  .  #
                #2    1#
                #  .  3#
                ######## """)
        layout = Layout(repr_test, TestLayoutChecks.layout_chars, 4)
        layout2 = eval(repr(layout))
        self.assertEqual(layout, layout2)

    def test_as_mesh(self):
        simple_layout = (
            """ ####
                #. #
                #### """)
        layout = Layout(simple_layout, TestLayoutChecks.layout_chars, 0)
        mesh = layout.as_mesh()
        target = Mesh(4, 3, data = list('#####. #####'))
        self.assertEqual(target, mesh)

    def test_mesh_shape(self):
        simple_layout = (
            """ ####
                #. #
                #### """)
        layout = Layout(simple_layout, TestLayoutChecks.layout_chars, 0)
        mesh = layout.as_mesh()
        self.assertEqual(mesh.shape, (4, 3))

    def test_empty_lines(self):
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

        self.assertEqual(Layout(simple_layout_1, TestLayoutChecks.layout_chars, 0),
                         Layout(simple_layout_2, TestLayoutChecks.layout_chars, 0))

    def test_from_file(self):
        test_l = (
            """ ######
                #0   #
                #    #
                #   1#
                ###### """)
        layout = Layout.from_file("test/test_layout.layout", TestLayoutChecks.layout_chars, 2)
        self.assertEqual(layout, Layout(test_l, TestLayoutChecks.layout_chars, 2))

