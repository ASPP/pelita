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

class TestIsAdjacent(unittest.TestCase):

    def test_is_adjacent(self):
        self.assertTrue(is_adjacent((0,0), (1,0)))
        self.assertTrue(is_adjacent((0,0), (0,1)))
        self.assertFalse(is_adjacent((0,0), (1,1)))

        self.assertTrue(is_adjacent((1,0), (0,0)))
        self.assertTrue(is_adjacent((0,1), (0,0)))
        self.assertFalse(is_adjacent((1,1), (0,0)))

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

    def test_wrong_bot_order(self):
        unordered = (
            """ #######
                #3    #
                #2 0  #
                #    1#
                ####### """)
        # this should not raise an exception, unfortunately there isn't such a
        # thing in unittest
        l = Layout(unordered, 4)

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

    def test_init_data(self):
        m = Mesh(2, 2, data=[1, 2, 3, 4])
        self.assertEqual(m.values(), [1,2,3,4])
        self.assertRaises(TypeError, Mesh, 2, 2, data='abcd')
        self.assertRaises(ValueError, Mesh, 2, 2, data=[1,2,3])

    def test_len(self):
        m = Mesh(2, 2)
        self.assertEqual(len(m), 4)

    def test_str(self):
        m = Mesh(2, 2)
        m._set_data([1, 2, 3, 4])
        self.assertEqual(str(m), '[1, 2]\n[3, 4]\n')

    def test_repr(self):
        m = Mesh(2, 2, data=[1, 2, 3,4])
        rep = m.__repr__()
        m2 = eval(rep)
        self.assertEqual(m, m2)

    def test_copy(self):
        m = Mesh(2,2)
        m2 = m
        m3 = m.copy()
        m[1,1] = True
        self.assertTrue(m2[1,1])
        self.assertFalse(m3[1,1])

class TestCTFUniverse(unittest.TestCase):

    def test_init(self):
        test_layout3 = (
        """ ##################
            #0#.  .  # .     #
            #1#####    #####2#
            #     . #  .  .#3#
            ################## """)
        universe = CTFUniverse(test_layout3, 4)
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
        self.assertEqual(target, universe.food_mesh)
        target_food_list = [(1, 3), (1, 6), (1, 11), (3, 6), (3,11), (3, 14),  ]
        self.assertEqual(target_food_list, universe.food_list)

        odd_layout = (
            """ #####
                #0 1#
                ##### """)
        self.assertRaises(UniverseException, CTFUniverse, odd_layout, 2)

        odd_bots = (
            """ ####
                #01#
                #2 #
                #### """)
        self.assertRaises(UniverseException, CTFUniverse, odd_bots, 3)

        test_layout4 = (
            """ ######
                #0  1#
                #2  3#
                ###### """)
        universe = CTFUniverse(test_layout4, 4)
        self.assertEqual(universe.red_team, [0,2])
        self.assertEqual(universe.blue_team, [1,3])
        self.assertEqual(universe.red_zone, (0, 2))
        self.assertEqual(universe.blue_zone, (3, 5))

    def test_in_zone_on_team(self):
        test_layout4 = (
            """ ######
                #0  1#
                #2  3#
                ###### """)
        universe = CTFUniverse(test_layout4, 4)

        self.assertTrue(universe.in_red_zone(0))
        self.assertTrue(universe.in_red_zone(2))
        self.assertTrue(universe.in_blue_zone(1))
        self.assertTrue(universe.in_blue_zone(3))
        self.assertFalse(universe.in_red_zone(1))
        self.assertFalse(universe.in_red_zone(3))
        self.assertFalse(universe.in_blue_zone(0))
        self.assertFalse(universe.in_blue_zone(2))

        self.assertTrue(universe.on_red_team(0))
        self.assertTrue(universe.on_red_team(2))
        self.assertTrue(universe.on_blue_team(1))
        self.assertTrue(universe.on_blue_team(3))
        self.assertFalse(universe.on_red_team(1))
        self.assertFalse(universe.on_red_team(3))
        self.assertFalse(universe.on_blue_team(0))
        self.assertFalse(universe.on_blue_team(2))

    def test_is_harvester_is_destroyer(self):
        test_layout4 = (
            """ ######
                #0 2 #
                # 1 3#
                ###### """)
        universe = CTFUniverse(test_layout4, 4)
        self.assertTrue(universe.is_harvester(1))
        self.assertTrue(universe.is_harvester(2))
        self.assertFalse(universe.is_harvester(0))
        self.assertFalse(universe.is_harvester(3))

        self.assertTrue(universe.is_destroyer(0))
        self.assertTrue(universe.is_destroyer(3))
        self.assertFalse(universe.is_destroyer(1))
        self.assertFalse(universe.is_destroyer(2))

class TestCTFUniverseRules(unittest.TestCase):

    def test_get_legal_moves(self):
        test_legal = (
            """ ######
                #  # #
                #   ##
                #    #
                ###### """)
        universe = CTFUniverse(test_legal, 0)
        legal_moves_1_1 = universe.get_legal_moves((1,1))
        target = {east  : (1,2),
                  south : (2,1),
                  stop  : (1,1)}
        self.assertEqual(target, legal_moves_1_1)
        legal_moves_1_2 = universe.get_legal_moves((1,2))
        target = {west  : (1,1),
                  south : (2,2),
                  stop  : (1,2)}
        self.assertEqual(target, legal_moves_1_2)
        legal_moves_1_4 = universe.get_legal_moves((1,4))
        target = { stop  : (1,4)}
        self.assertEqual(target, legal_moves_1_4)
        legal_moves_2_1 = universe.get_legal_moves((2,1))
        target = {north  : (1,1),
                  east  : (2,2),
                  south : (3,1),
                  stop  : (2,1)}
        self.assertEqual(target, legal_moves_2_1)
        legal_moves_2_2 = universe.get_legal_moves((2,2))
        target = {north  : (1,2),
                  east  : (2,3),
                  south : (3,2),
                  west : (2,1),
                  stop  : (2,2)}
        self.assertEqual(target, legal_moves_2_2)
        legal_moves_2_3 = universe.get_legal_moves((2,3))
        target = { south : (3,3),
                  west : (2,2),
                  stop  : (2,3)}
        self.assertEqual(target, legal_moves_2_3)
        legal_moves_3_1 = universe.get_legal_moves((3,1))
        target = {north  : (2,1),
                  east  : (3,2),
                  stop  : (3,1)}
        self.assertEqual(target, legal_moves_3_1)
        legal_moves_3_2 = universe.get_legal_moves((3,2))
        target = {north  : (2,2),
                  east  : (3,3),
                  west : (3,1),
                  stop  : (3,2)}
        self.assertEqual(target, legal_moves_3_2)
        # 3,3 has the same options as 3,2
        legal_moves_3_4 = universe.get_legal_moves((3,4))
        target = {west  : (3,3),
                  stop  : (3,4)}
        self.assertEqual(target, legal_moves_3_4)

    def test_one(self):

        test_start = (
            """ ######
                #0   #
                #.  1#
                ###### """)
        number_bots = 2
        universe = CTFUniverse(test_start, number_bots)
        universe.move_bot(1, west)
        test_first_move = (
            """ ######
                #0   #
                #. 1 #
                ###### """)
        self.assertEqual(str(universe),
                str(Layout(test_first_move, number_bots).as_mesh()))
        test_second_move = (
            """ ######
                #0   #
                #.1  #
                ###### """)
        universe.move_bot(1, west)
        self.assertEqual(str(universe),
                str(Layout(test_second_move, number_bots).as_mesh()))
        test_eat_food = (
            """ ######
                #0   #
                #1   #
                ###### """)
        universe.move_bot(1, west)
        self.assertEqual(str(universe),
                str(Layout(test_eat_food, number_bots).as_mesh()))
        self.assertEqual(universe.food_list, [])
        self.assertEqual(universe.blue_score, 1)
        test_destruction = (
            """ ######
                #    #
                #0  1#
                ###### """)
        universe.move_bot(0, south)
        self.assertEqual(str(universe),
                str(Layout(test_destruction, number_bots).as_mesh()))


if __name__ == '__main__':
    unittest.main()

