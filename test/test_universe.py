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
        stripped = [c for c in Layout.strip_layout(test_layout)]
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
        self.assertRaises(LayoutEncodingException, Layout.check_layout,
                Layout.strip_layout(illeagal_layout), 0)

    def test_not_enough_bots(self):
        not_enough_bots = (
        """ #######
            #0    #
            #  1  #
            #    2#
            ####### """)
        self.assertRaises(LayoutEncodingException, Layout.check_layout,
                Layout.strip_layout(not_enough_bots), 5)

    def test_too_many_bots(self):
        too_many_bots = (
        """ #######
            #0    #
            #  0  #
            #    2#
            ####### """)
        self.assertRaises(LayoutEncodingException, Layout.check_layout,
                Layout.strip_layout(too_many_bots), 3)

    def test_wrong_shape(self):
        wrong_shape = (
        """ #######
            #  #
            #   #
            #    #
            ######  """)
        self.assertRaises(LayoutEncodingException, Layout.check_layout,
                Layout.strip_layout(wrong_shape), 3)

    def test_str(self):
        simple_layout = (
            """ ####
                #. #
                #### """)
        layout = Layout(simple_layout, 0)
        target = '####\n'+\
                 '#. #\n'+\
                 '####'
        self.assertEqual(target, str(layout))

    def test_as_mesh(self):
        simple_layout = (
            """ ####
                #. #
                #### """)
        layout = Layout(simple_layout, 0)
        mesh = layout.as_mesh()
        target = Mesh(3,4)
        target._set_data(list('#####. #####'))
        self.assertEqual(target, mesh)

class TestLayoutOps(unittest.TestCase):

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
        self.assertEqual(Layout.layout_shape(Layout.strip_layout(large_shape)), (5, 7))

    def test_convert_to_grid(self):
        test_layout = (
        """ #######
            #c    #
            #  .  #
            #    o#
            ####### """)
        converted = convert_to_grid(Layout.strip_layout(test_layout))
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
        layout = Layout(test_layout, number_bots)
        mesh = layout.as_mesh()
        initial_pos = initial_positions(mesh, number_bots)
        target = [(1, 1), (2, 3), (3, 5)]
        self.assertEqual(target, initial_pos)
        # also test the side-effect of initial_positions()
        target = Mesh(5, 7)
        target._set_data(list('########     ##     ##     ########'))
        self.assertEqual(target, mesh)

        # now for a somewhat more realistic example
        test_layout2 = (
        """ ##################
            #0#      #       #
            #1#####    #####2#
            #       #      #3#
            ################## """)
        number_bots = 4
        layout = Layout(test_layout2, number_bots)
        mesh = layout.as_mesh()
        initial_pos = initial_positions(mesh, number_bots)
        target = [(1, 1), (2, 1), (2, 16), (3, 16)]
        self.assertEqual(target, initial_pos)
        # also test the side-effect of initial_positions()
        target = Mesh(5, 18)
        target._set_data(list('################### #      #       #'+\
                '# #####    ##### ##       #      # ###################'))

        self.assertEqual(target, mesh)

    def test_extract_food(self):
        food_layout = (
        """ #######
            #.  . #
            #  .  #
            # .  .#
            ####### """)
        layout = Layout(food_layout, 0)
        mesh = layout.as_mesh()
        food_mesh = extract_food(mesh)
        target = Mesh(5,7)
        target._set_data([
            False, False, False, False, False, False, False,
            False, True , False, False, True , False, False,
            False, False, False, True , False, False, False,
            False, False, True , False, False, True , False,
            False, False, False, False, False, False, False])
        self.assertEqual(target, food_mesh)

class TestMesh(unittest.TestCase):

    def test_init(self):
        m = Mesh(2, 2)
        self.assertEqual(m.values(), [None, None, None, None])
        self.assertEqual(m.shape, (2, 2))
        m = Mesh(0, 0)
        self.assertEqual(m.values(), [])
        self.assertEqual(m.shape, (0, 0))
        m = Mesh(1, 4)
        self.assertEqual(m.values(), [None, None, None, None])
        self.assertEqual(m.shape, (1, 4))
        m = Mesh(4, 1)
        self.assertEqual(m.values(), [None, None, None, None])
        self.assertEqual(m.shape, (4, 1))

    def test_indices(self):
        m = Mesh(2,3)
        target = [(0,0), (0, 1), (0, 2), (1, 0), (1, 1), (1, 2)]
        self.assertEqual(target, m.keys())

    def test_index_linear_to_tuple(self):
        m = Mesh(3,4)
        for (i,(h,w)) in enumerate(m.iterkeys()):
            self.assertEqual(m._index_linear_to_tuple(i), (h,w))

    def test_index_tuple_to_linear(self):
        m = Mesh(3,4)
        for (i,(h,w)) in enumerate(m.iterkeys()):
            self.assertEqual(m._index_tuple_to_linear((h,w)), i)

    def test_getitem(self):
        m = Mesh(2, 2)
        m._data = [1, 2, 3, 4]
        self.assertEqual(m[0, 0], 1)
        self.assertEqual(m[0, 1], 2)
        self.assertEqual(m[1, 0], 3)
        self.assertEqual(m[1, 1], 4)
        self.assertRaises(IndexError, m.__getitem__, (3, 0))
        self.assertRaises(IndexError, m.__getitem__, (-1, 0))
        self.assertRaises(IndexError, m.__getitem__, (0, 3))
        self.assertRaises(IndexError, m.__getitem__, (0, -1))

    def test_setitem(self):
        m = Mesh(2, 2)
        m[0, 0] = 1
        m[0, 1] = 2
        m[1, 0] = 3
        m[1, 1] = 4
        self.assertEqual(m._data, [1, 2, 3, 4])
        self.assertRaises(IndexError, m.__setitem__, (3, 0), 1)
        self.assertRaises(IndexError, m.__setitem__, (-1, 0), 1)
        self.assertRaises(IndexError, m.__setitem__, (0, 3), 1)
        self.assertRaises(IndexError, m.__setitem__, (0, -1), 1)

    def test_iter(self):
        m = Mesh(2, 2)
        self.assertEqual([i for i in m], [(0,0), (0, 1), (1, 0), (1, 1)])

    def test_set_data(self):
        m = Mesh(2, 2)
        m._set_data([1, 2, 3, 4])
        self.assertEqual(m.values(), [1,2,3,4])
        self.assertRaises(TypeError, m._set_data, 'abcd')
        self.assertRaises(ValueError, m._set_data, [1,2,3])

    def test_len(self):
        m = Mesh(2, 2)
        self.assertEqual(len(m), 4)

    def test_str(self):
        m = Mesh(2, 2)
        m._set_data([1, 2, 3, 4])
        self.assertEqual(str(m), '[1, 2]\n[3, 4]\n')



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
        self.assertEqual(universe.initial_pos,
                [(1, 1), (2, 1), (2, 16), (3, 16)])
        # this checks that the methods extracts the food, and the initial
        # positions from the raw layout
        target = Mesh(5, 18)
        target._set_data(list('################### #      #       #'+\
                '# #####    ##### ##       #      # ###################'))
        self.assertEqual(target, universe.mesh)
        target._set_data([
            False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False,
            False, False, False, True,  False, False, True,  False, False, False, False, True,  False, False, False, False, False, False,
            False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False,
            False, False, False, False, False, False, True,  False, False, False, False, True,  False, False, True,  False, False, False,
            False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False])
        self.assertEqual(target, universe.food_positions)

if __name__ == '__main__':
    unittest.main()

