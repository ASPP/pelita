import unittest
from pelita.universe import *

class TestLayoutChecks(unittest.TestCase):

    def test_strip_layout(self):
        test_layout = (
        """ #######
            #c    #
            #  .  #
            #    o#
            ####### """)
        stripped = [c for c in strip_layout(test_layout)]
        target = ['#', '#', '#', '#', '#', '#', '#', '\n',
                  '#', 'c', ' ', ' ', ' ', ' ', '#', '\n',
                  '#', ' ', ' ', '.', ' ', ' ', '#', '\n',
                  '#', ' ', ' ', ' ', ' ', 'o', '#', '\n',
                  '#', '#', '#', '#', '#', '#', '#', '\n']
        self.assertEqual(stripped, target)

    def test_illegal_character(self):
        illeagal_layout = (
        """ #######
            #c    #
            #  f  #
            #    o#
            ####### """)
        self.assertRaises(LayoutEncodingException, check_layout,
                strip_layout(illeagal_layout), 0)

    def test_not_enough_bots(self):
        not_enough_bots = (
        """ #######
            #1    #
            #  2  #
            #    3#
            ####### """)
        self.assertRaises(LayoutEncodingException, check_layout,
                strip_layout(not_enough_bots), 5)

    def test_too_many_bots(self):
        too_many_bots = (
        """ #######
            #1    #
            #  1  #
            #    3#
            ####### """)
        self.assertRaises(LayoutEncodingException, check_layout,
                strip_layout(too_many_bots), 3)

    def test_wrong_shape(self):
        wrong_shape = (
        """ #######
            #  #
            #   #
            #    #
            ######  """)
        self.assertRaises(LayoutEncodingException, check_layout,
                strip_layout(wrong_shape), 3)

class TestLayoutOps(unittest.TestCase):

    def test_layout_shape(self):
        small_shape = (
        """ ###
            # #
            ### """)
        self.assertEqual(layout_shape(strip_layout(small_shape)), (3,3))

        large_shape = (
        """ #######
            #     #
            #     #
            #     #
            ####### """)
        self.assertEqual(layout_shape(strip_layout(large_shape)), (5,7))

    def test_convert_to_grid(self):
        test_layout = (
        """ #######
            #c    #
            #  .  #
            #    o#
            ####### """)
        converted = convert_to_grid(strip_layout(test_layout))
        target = [['#', '#', '#', '#', '#', '#', '#'],
                  ['#', 'c', ' ', ' ', ' ', ' ', '#'],
                  ['#', ' ', ' ', '.', ' ', ' ', '#'],
                  ['#', ' ', ' ', ' ', ' ', 'o', '#'],
                  ['#', '#', '#', '#', '#', '#', '#']]
        self.assertEqual(converted, target)

    def test_get_initial_positions(self):
        test_layout = (
        """ #######
            #1    #
            #  2  #
            #    3#
            ####### """)
        number_bots = 3
        stripped = strip_layout(test_layout)
        check_layout(stripped, number_bots)
        shape = layout_shape(stripped)
        grid = convert_to_grid(stripped)
        initial_pos = initial_positions(grid, shape, number_bots)
        target = [(1, 1), (2,3), (3,5)]
        self.assertEqual(target, initial_pos)

        # now for a somewhat more realistic example
        test_layout2 = (
        """ ##################
            #1#      #       #
            #2#####    #####3#
            #       #      #4#
            ################## """)
        number_bots = 4
        stripped = strip_layout(test_layout2)
        check_layout(stripped, number_bots)
        shape = layout_shape(stripped)
        grid = convert_to_grid(stripped)
        initial_pos = initial_positions(grid, shape, number_bots)
        target = [(1, 1), (2, 1), (2, 16), (3, 16)]
        self.assertEqual(target, initial_pos)

if __name__ == '__main__':
    unittest.main()

