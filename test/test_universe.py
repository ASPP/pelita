import unittest
from pelita.universe import *

class TestNewPositions(unittest.TestCase):

    def test_new_positions(self):
        current_position = (1, 1)
        new = new_positions(current_position)
        target = { north : (0, 1),
                    south : (2, 1),
                    west  : (1, 0),
                    east  : (1, 2),
                    stop  : (1, 1) }
        self.assertEqual(target, new)

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
                  '#', '#', '#', '#', '#', '#', '#']
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
            #0    #
            #  1  #
            #    2#
            ####### """)
        self.assertRaises(LayoutEncodingException, check_layout,
                strip_layout(not_enough_bots), 5)

    def test_too_many_bots(self):
        too_many_bots = (
        """ #######
            #0    #
            #  0  #
            #    2#
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
            #0    #
            #  1  #
            #    2#
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
            #0#      #       #
            #1#####    #####2#
            #       #      #3#
            ################## """)
        number_bots = 4
        stripped = strip_layout(test_layout2)
        check_layout(stripped, number_bots)
        shape = layout_shape(stripped)
        grid = convert_to_grid(stripped)
        initial_pos = initial_positions(grid, shape, number_bots)
        target = [(1, 1), (2, 1), (2, 16), (3, 16)]
        self.assertEqual(target, initial_pos)

    def test_extract_food(self):
        food_layout = (
        """ #######
            #.  . #
            #  .  #
            # .  .#
            ####### """)
        stripped = strip_layout(food_layout)
        check_layout(stripped, 0)
        shape = layout_shape(stripped)
        grid = convert_to_grid(stripped)
        food_grid = extract_food(grid, shape)
        target = [
            [False, False, False, False, False, False, False],
            [False, True , False, False, True , False, False],
            [False, False, False, True , False, False, False],
            [False, False, True , False, False, True , False],
            [False, False, False, False, False, False, False]]

        self.assertEqual(target, food_grid)

class TestUniverse(unittest.TestCase):

    def test_init(self):
        test_layout3 = (
        """ ##################
            #0#.  .  # .     #
            #1#####    #####2#
            #     . #  .  .#3#
            ################## """)
        number_bots = 4
        universe = Universe(test_layout3, 4)
        self.assertEqual(universe.shape, (5, 18))
        self.assertEqual(universe.initial_pos,
                [(1, 1), (2, 1), (2, 16), (3, 16)])
        # this checks that the methods extracts the food, and the initial
        # positions from the raw layout
        target_layout = [
             ['#', '#', '#', '#', '#', '#', '#', '#', '#', '#', '#', '#', '#', '#', '#', '#', '#', '#'],
             ['#', ' ', '#', ' ', ' ', ' ', ' ', ' ', ' ', '#', ' ', ' ', ' ', ' ', ' ', ' ', ' ', '#'],
             ['#', ' ', '#', '#', '#', '#', '#', ' ', ' ', ' ', ' ', '#', '#', '#', '#', '#', ' ', '#'],
             ['#', ' ', ' ', ' ', ' ', ' ', ' ', ' ', '#', ' ', ' ', ' ', ' ', ' ', ' ', '#', ' ', '#'],
             ['#', '#', '#', '#', '#', '#', '#', '#', '#', '#', '#', '#', '#', '#', '#', '#', '#', '#']]
        self.assertEqual(target_layout, universe.layout)
        target_food_pos = [
            [False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False],
            [False, False, False, True,  False, False, True,  False, False, False, False, True,  False, False, False, False, False, False],
            [False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False],
            [False, False, False, False, False, False, True,  False, False, False, False, True,  False, False, True,  False, False, False],
            [False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False]]
        self.assertEqual(target_food_pos, universe.food_positions)

if __name__ == '__main__':
    unittest.main()

