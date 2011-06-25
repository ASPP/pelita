import unittest
from pelita.layout import Layout
from pelita.mesh import Mesh
from pelita.universe import *

class TestCTFUniverseStaticmethods(unittest.TestCase):

    def test_get_initial_positions(self):
        test_layout = (
            """ #######
                #0    #
                #  1  #
                #    2#
                ####### """)
        number_bots = 3
        layout = Layout(test_layout, CTFUniverse.layout_chars, number_bots)
        mesh = layout.as_mesh()
        initial_pos = CTFUniverse.extract_initial_positions(mesh, number_bots)
        target = [(1, 1), (3, 2), (5, 3)]
        self.assertEqual(target, initial_pos)
        # also test the side-effect of initial_positions()
        target = Mesh(7, 5, data =list('########     ##     ##     ########'))
        self.assertEqual(target, mesh)

        # now for a somewhat more realistic example
        test_layout2 = (
            """ ##################
                #0#      #       #
                #1#####    #####2#
                #       #      #3#
                ################## """)
        number_bots = 4
        layout = Layout(test_layout2, CTFUniverse.layout_chars, number_bots)
        mesh = layout.as_mesh()
        initial_pos = CTFUniverse.extract_initial_positions(mesh, number_bots)
        target = [(1, 1), (1, 2), (16, 2), (16, 3)]
        self.assertEqual(target, initial_pos)
        # also test the side-effect of initial_positions()
        target = Mesh(18, 5, data = list('################### #      #       #'+\
                '# #####    ##### ##       #      # ###################'))
        self.assertEqual(target, mesh)

    def test_extract_food(self):
        food_layout = (
            """ #######
                #.  . #
                #  .  #
                # .  .#
                ####### """)
        layout = Layout(food_layout, CTFUniverse.layout_chars, 0)
        mesh = layout.as_mesh()
        food_mesh = CTFUniverse.extract_food_mesh(mesh)
        target = Mesh(7, 5, data=[
            False, False, False, False, False, False, False,
            False, True , False, False, True , False, False,
            False, False, False, True , False, False, False,
            False, False, True , False, False, True , False,
            False, False, False, False, False, False, False])
        self.assertEqual(target, food_mesh)


    def test_new_positions(self):
        current_position = (1, 1)
        new = CTFUniverse.new_positions(current_position)
        target = { north : (1, 0),
                    south : (1, 2),
                    west  : (0, 1),
                    east  : (2, 1),
                    stop  : (1, 1) }
        self.assertEqual(target, new)

    def test_is_adjacent(self):
        self.assertTrue(CTFUniverse.is_adjacent((0, 0), (1, 0)))
        self.assertTrue(CTFUniverse.is_adjacent((0, 0), (0, 1)))
        self.assertFalse(CTFUniverse.is_adjacent((0, 0), (1, 1)))

        self.assertTrue(CTFUniverse.is_adjacent((1, 0), (0, 0)))
        self.assertTrue(CTFUniverse.is_adjacent((0, 1), (0, 0)))
        self.assertFalse(CTFUniverse.is_adjacent((1, 1), (0, 0)))

class TestCTFUniverse(unittest.TestCase):

    def test_init(self):
        test_layout3 = (
        """ ##################
            #0#.  .  # .     #
            #1#####    #####2#
            #     . #  .  .#3#
            ################## """)
        universe = CTFUniverse(test_layout3, 4)
        # this checks that the methods extracts the food, and the initial
        # positions from the raw layout
        target_mesh = Mesh(18, 5, data = list('################### #      #       #'+\
                '# #####    ##### ##       #      # ###################'))
        self.assertEqual(target_mesh, universe.mesh)
        target_food_list = Mesh(18, 5, data=[
            False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False,
            False, False, False, True,  False, False, True,  False, False, False, False, True,  False, False, False, False, False, False,
            False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False,
            False, False, False, False, False, False, True,  False, False, False, False, True,  False, False, True,  False, False, False,
            False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False])
        self.assertEqual(target_food_list, universe.food_mesh)
        target_food_list = [(3, 1), (6, 1), (11, 1), (6, 3), (11, 3), (14, 3),  ]
        self.assertEqual(target_food_list, universe.food_list)

        self.assertEqual([b.initial_pos for b in universe.bots],
                [(1, 1), (1, 2), (16, 2), (16, 3)]

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

    def test_bot_teams(self):

        test_layout4 = (
            """ ######
                #0  1#
                #2  3#
                ###### """)
        universe = CTFUniverse(test_layout4, 4)

        red_team = Team('red', (0, 2))
        blue_team = Team('blue', (3, 5))
        red_team.add_bot(Bot(0, (1, 1), red_team))
        red_team.add_bot(Bot(2, (2, 1), red_team))
        blue_team.add_bot(Bot(1,(1, 4), blue_team))
        blue_team.add_bot(Bot(3,(2, 4), blue_team))

        # since the Team and Bot objects are mutually composite
        # calling Team.__eq__() inherently also calls Bot.__eq__()
        self.assertEqual(universe.teams[0], red_team)
        self.assertEqual(universe.teams[1], blue_team)

        self.assertEqual(universe.bots[0].team, red_team)
        self.assertEqual(universe.bots[2].team, red_team)
        self.assertEqual(universe.bots[1].team, blue_team)
        self.assertEqual(universe.bots[3].team, blue_team)

        self.assertTrue(universe.bots[0].in_own_zone)
        self.assertTrue(universe.bots[1].in_own_zone)
        self.assertTrue(universe.bots[2].in_own_zone)
        self.assertTrue(universe.bots[3].in_own_zone)

        test_layout4 = (
            """ ######
                #1  0#
                #3  2#
                ###### """)
        universe = CTFUniverse(test_layout4, 4)

        self.assertFalse(universe.bots[0].in_own_zone)
        self.assertFalse(universe.bots[1].in_own_zone)
        self.assertFalse(universe.bots[2].in_own_zone)
        self.assertFalse(universe.bots[3].in_own_zone)

        test_layout4 = (
            """ ######
                #0 2 #
                # 1 3#
                ###### """)
        universe = CTFUniverse(test_layout4, 4)
        self.assertTrue(universe.bots[1].is_harvester)
        self.assertTrue(universe.bots[2].is_harvester)
        self.assertFalse(universe.bots[0].is_harvester)
        self.assertFalse(universe.bots[3].is_harvester)
        self.assertFalse(universe.bots[1].is_destroyer)
        self.assertFalse(universe.bots[2].is_destroyer)
        self.assertTrue(universe.bots[0].is_destroyer)
        self.assertTrue(universe.bots[3].is_destroyer)

class TestCTFUniverseRules(unittest.TestCase):

    def test_get_legal_moves(self):
        test_legal = (
            """ ######
                #  # #
                #   ##
                #    #
                ###### """)
        universe = CTFUniverse(test_legal, 0)
        legal_moves_1_1 = universe.get_legal_moves((1, 1))
        target = {east  : (2, 1),
                  south : (1, 2),
                  stop  : (1, 1)}
        self.assertEqual(target, legal_moves_1_1)
        legal_moves_2_1 = universe.get_legal_moves((2, 1))
        target = {west  : (1, 1),
                  south : (2, 2),
                  stop  : (2, 1)}
        self.assertEqual(target, legal_moves_2_1)
        legal_moves_4_1 = universe.get_legal_moves((4, 1))
        target = { stop : (4, 1)}
        self.assertEqual(target, legal_moves_4_1)
        legal_moves_1_2 = universe.get_legal_moves((1, 2))
        target = {north : (1, 1),
                  east  : (2, 2),
                  south : (1, 3),
                  stop  : (1, 2)}
        self.assertEqual(target, legal_moves_1_2)
        legal_moves_2_2 = universe.get_legal_moves((2, 2))
        target = {north : (2, 1),
                  east  : (3, 2),
                  south : (2, 3),
                  west  : (1, 2),
                  stop  : (2, 2)}
        self.assertEqual(target, legal_moves_2_2)
        legal_moves_3_2 = universe.get_legal_moves((3, 2))
        target = {south : (3, 3),
                  west  : (2, 2),
                  stop  : (3, 2)}
        self.assertEqual(target, legal_moves_3_2)
        legal_moves_1_3 = universe.get_legal_moves((1, 3))
        target = {north : (1, 2),
                  east  : (2, 3),
                  stop  : (1, 3)}
        self.assertEqual(target, legal_moves_1_3)
        legal_moves_2_3 = universe.get_legal_moves((2, 3))
        target = {north : (2, 2),
                  east  : (3, 3),
                  west  : (1, 3),
                  stop  : (2, 3)}
        self.assertEqual(target, legal_moves_2_3)
        # 3, 3 has the same options as 2, 3
        legal_moves_4_3 = universe.get_legal_moves((4, 3))
        target = {west  : (3, 3),
                  stop  : (4, 3)}
        self.assertEqual(target, legal_moves_4_3)

    def test_move_bot_exceptions(self):
        test_move_bot = (
            """ ######
                #  #0#
                # 3 ##
                #2  1#
                ###### """)
        universe = CTFUniverse(test_move_bot, 4)

        self.assertRaises(IllegalMoveException, universe.move_bot, 0, 'FOOBAR')

        self.assertRaises(IllegalMoveException, universe.move_bot, 0, north)
        self.assertRaises(IllegalMoveException, universe.move_bot, 0, west)
        self.assertRaises(IllegalMoveException, universe.move_bot, 0, south)
        self.assertRaises(IllegalMoveException, universe.move_bot, 0, east)

        self.assertRaises(IllegalMoveException, universe.move_bot, 1, north)
        self.assertRaises(IllegalMoveException, universe.move_bot, 1, east)
        self.assertRaises(IllegalMoveException, universe.move_bot, 1, south)

        self.assertRaises(IllegalMoveException, universe.move_bot, 2, west)
        self.assertRaises(IllegalMoveException, universe.move_bot, 2, south)

    def test_reset_bot(self):
        test_reset_bot = (
            """ ########
                #0     #
                #2    3#
                #     1#
                ######## """)
        number_bots = 4
        universe = CTFUniverse(test_reset_bot, number_bots)
        self.assertEqual(str(universe),
                str(Layout(test_reset_bot, CTFUniverse.layout_chars, number_bots).as_mesh()))
        test_shuffle = (
            """ ########
                #   0 3#
                # 1    #
                # 2    #
                ######## """)
        universe.bots[0].move((4, 1))
        universe.bots[1].move((2, 2))
        universe.bots[2].move((2, 3))
        universe.bots[3].move((6, 1))
        self.assertEqual(str(universe),
                str(Layout(test_shuffle, CTFUniverse.layout_chars, number_bots).as_mesh()))
        universe.bots[0].reset()
        universe.bots[1].reset()
        universe.bots[2].reset()
        universe.bots[3].reset()
        self.assertEqual(str(universe),
                str(Layout(test_reset_bot, CTFUniverse.layout_chars, number_bots).as_mesh()))

    def test_one(self):

        test_start = (
            """ ######
                #0 . #
                #.  1#
                ###### """)
        number_bots = 2
        universe = CTFUniverse(test_start, number_bots)
        universe.move_bot(1, west)
        test_first_move = (
            """ ######
                #0 . #
                #. 1 #
                ###### """)
        self.assertEqual(str(universe),
                str(Layout(test_first_move, CTFUniverse.layout_chars, number_bots).as_mesh()))
        test_second_move = (
            """ ######
                #0 . #
                #.1  #
                ###### """)
        universe.move_bot(1, west)
        self.assertEqual(str(universe),
                str(Layout(test_second_move, CTFUniverse.layout_chars, number_bots).as_mesh()))
        test_eat_food = (
            """ ######
                #0 . #
                #1   #
                ###### """)
        self.assertEqual(universe.food_list, [(3, 1), (1, 2)])
        universe.move_bot(1, west)
        self.assertEqual(str(universe),
                str(Layout(test_eat_food, CTFUniverse.layout_chars, number_bots).as_mesh()))
        self.assertEqual(universe.food_list, [(3, 1)])
        self.assertEqual(universe.teams[1].score, 1)
        test_destruction = (
            """ ######
                #  . #
                #0  1#
                ###### """)
        universe.move_bot(0, south)
        self.assertEqual(str(universe),
                str(Layout(test_destruction, CTFUniverse.layout_chars ,number_bots).as_mesh()))
        test_red_score = (
            """ ######
                #  0 #
                #   1#
                ###### """)
        universe.move_bot(0, north)
        universe.move_bot(0, east)
        universe.move_bot(0, east)
        self.assertEqual(str(universe),
                str(Layout(test_red_score, CTFUniverse.layout_chars, number_bots).as_mesh()))
        self.assertEqual(universe.food_list, [])
        self.assertEqual(universe.teams[0].score, 1)

if __name__ == '__main__':
    unittest.main()

