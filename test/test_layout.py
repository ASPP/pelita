import unittest

from pelita.datamodel import maze_components
from pelita.layout import *


class TestLayoutModule(unittest.TestCase):

    def test_load_layout(self):
        # check that too many layout args raise an error
        layout_name = "layout_normal_with_dead_ends_001"
        layout_file = "test/test_layout.layout"
        self.assertRaises(ValueError, load_layout,
                layout_name=layout_name,
                layout_file=layout_file)
        # check that unknown layout_name raises an appropriate error
        self.assertRaises(ValueError, load_layout, layout_name="foobar")
        # check that a non existent file raises an error
        self.assertRaises(IOError, load_layout, layout_file="foobar")
        # check that stuff behaves as it should
        self.assertEqual("layout_normal_with_dead_ends_001", load_layout(layout_name=layout_name)[0])
        self.assertEqual("test/test_layout.layout", load_layout(layout_file=layout_file)[0])


    def test_get_available_layouts(self):
        available = get_available_layouts()
        self.assertEqual(600, len(available))
        # now also test the filter
        available = get_available_layouts(filter='normal_without_dead_ends')
        self.assertEqual(100, len(available))

    def test_get_layout_by_name(self):
        # sorry about the indentation, but this is exactly how the string is
        with open('layouts/normal_with_dead_ends_001.layout', 'rU') as file:
            target_layout = file.read()
        loaded = get_layout_by_name('layout_normal_with_dead_ends_001')
        self.assertEqual(target_layout, loaded)

    def test_get_random_layout(self):
        available = get_available_layouts()
        random1 = get_random_layout()
        random2 = get_random_layout()
        self.assertNotEqual(random1, random2,
                'Testing randomized function, may fail sometimes.')

    def test_get_random_layout_returns_correct_layout(self):
        name, layout = get_random_layout()
        layout2 = get_layout_by_name(name)
        self.assertEqual(layout, layout2)


class TestLayoutChecks(unittest.TestCase):
    layout_chars = maze_components

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
