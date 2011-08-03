import unittest
from pelita.containers import Mesh
from pelita.layout import *

class TestLayoutChecks(unittest.TestCase):

    # we replicate the CTFUniverse layout_chars here
    wall   = '#'
    food   = '.'
    harvester = 'c'
    destroyer = 'o'
    free   = ' '

    layout_chars = [wall, food, harvester, destroyer, free]

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
