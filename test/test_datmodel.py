import unittest
import json
from pelita.layout import Layout
from pelita.containers import Mesh
from pelita.datamodel import *
from pelita.messaging.json_convert import json_converter


# the legal chars for a basic CTFUniverse
# see also: create_CTFUniverse factory.
layout_chars = maze_components

class TestStaticmethods(unittest.TestCase):

    def test_new_pos(self):
        self.assertEqual(new_pos((1, 1), north), (1, 0))
        self.assertEqual(new_pos((1, 1), south), (1, 2))
        self.assertEqual(new_pos((1, 1), east), (2, 1))
        self.assertEqual(new_pos((1, 1), west), (0, 1))
        self.assertEqual(new_pos((1, 1), stop), (1, 1))

        self.assertRaises(ValueError, new_pos, (0, 0), (1, 1))

    def test_diff_pos(self):
        self.assertEqual(north, diff_pos((1, 1), (1, 0)))
        self.assertEqual(south, diff_pos((1, 1), (1, 2)))
        self.assertEqual(east, diff_pos((1, 1), (2, 1)))
        self.assertEqual(west, diff_pos((1, 1), (0, 1)))
        self.assertEqual(stop, diff_pos((1, 1), (1, 1)))

        self.assertRaises(ValueError, diff_pos, (0, 0), (1, 1))

    def test_is_adjacent(self):
        self.assertTrue(is_adjacent((0, 0), (1, 0)))
        self.assertTrue(is_adjacent((0, 0), (0, 1)))
        self.assertFalse(is_adjacent((0, 0), (1, 1)))

        self.assertTrue(is_adjacent((1, 0), (0, 0)))
        self.assertTrue(is_adjacent((0, 1), (0, 0)))
        self.assertFalse(is_adjacent((1, 1), (0, 0)))

        self.assertFalse(is_adjacent((0, 0), (0, 0)))
        self.assertFalse(is_adjacent((1, 1), (1, 1)))

    def test_manhattan_dist(self):
        self.assertEqual(0, manhattan_dist((0, 0), (0, 0)))
        self.assertEqual(0, manhattan_dist((1, 1), (1, 1)))
        self.assertEqual(0, manhattan_dist((20, 20), (20, 20)))

        self.assertEqual(1, manhattan_dist((0, 0), (1, 0)))
        self.assertEqual(1, manhattan_dist((0, 0), (0, 1)))
        self.assertEqual(1, manhattan_dist((1, 0), (0, 0)))
        self.assertEqual(1, manhattan_dist((0, 1), (0, 0)))

        self.assertEqual(2, manhattan_dist((0, 0), (1, 1)))
        self.assertEqual(2, manhattan_dist((1, 1), (0, 0)))
        self.assertEqual(2, manhattan_dist((1, 0), (0, 1)))
        self.assertEqual(2, manhattan_dist((0, 1), (1, 0)))
        self.assertEqual(2, manhattan_dist((0, 0), (2, 0)))
        self.assertEqual(2, manhattan_dist((0, 0), (0, 2)))
        self.assertEqual(2, manhattan_dist((2, 0), (0, 0)))
        self.assertEqual(2, manhattan_dist((0, 2), (0, 0)))

        self.assertEqual(4, manhattan_dist((1, 2), (3, 4)))

    def test_get_initial_positions(self):


        test_layout = (
            """ #######
                #0    #
                #  1  #
                #    2#
                ####### """)
        number_bots = 3
        layout = Layout(test_layout, layout_chars, number_bots)
        mesh = layout.as_mesh()
        initial_pos = extract_initial_positions(mesh, number_bots)
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
        layout = Layout(test_layout2, layout_chars, number_bots)
        mesh = layout.as_mesh()
        initial_pos = extract_initial_positions(mesh, number_bots)
        target = [(1, 1), (1, 2), (16, 2), (16, 3)]
        self.assertEqual(target, initial_pos)
        # also test the side-effect of initial_positions()
        target = Mesh(18, 5, data = list('################### #      #       #'+\
                '# #####    ##### ##       #      # ###################'))
        self.assertEqual(target, mesh)


class TestBot(unittest.TestCase):

    def test_init_in_own_zone_is_harvester(self):
        bot = Bot(0, (1, 1), 0, (0, 3))
        self.assertEqual(bot.index, 0)
        self.assertEqual(bot.initial_pos, (1, 1))
        self.assertEqual(bot.current_pos, (1, 1))
        self.assertEqual(bot.team_index, 0)
        self.assertEqual(bot.homezone, (0, 3))
        self.assertTrue(bot.is_destroyer)
        self.assertFalse(bot.is_harvester)
        self.assertTrue(bot.in_own_zone)

        bot = Bot(1, (6, 6), 1, (3, 6), current_pos = (1, 1))
        self.assertEqual(bot.index, 1)
        self.assertEqual(bot.initial_pos, (6, 6))
        self.assertEqual(bot.current_pos, (1, 1))
        self.assertEqual(bot.team_index, 1)
        self.assertEqual(bot.homezone, (3, 6))
        self.assertFalse(bot.is_destroyer)
        self.assertTrue(bot.is_harvester)
        self.assertFalse(bot.in_own_zone)

    def test_eq_repr_cmp(self):
        black = Bot(0, (1, 1), 0, (0, 3))
        black2 = Bot(0, (1, 1), 0, (0, 3))
        white = Bot(1, (6, 6), 1, (3, 6), current_pos = (1, 1))
        self.assertNotEqual(black, white)
        self.assertEqual(black, black2)
        black3 = eval(repr(black))
        self.assertEqual(black, black3)
        self.assertEqual(black.__cmp__(black2), 0)
        self.assertEqual(black.__cmp__(white), -1)
        self.assertEqual(white.__cmp__(black),  1)

    def test_move_reset(self):
        black = Bot(0, (1, 1), 0, (0, 3))
        white = Bot(1, (6, 6), 1, (3, 6), current_pos = (1, 1))
        self.assertTrue(black.is_destroyer)
        black.current_pos = (4, 1)
        self.assertEqual(black.current_pos, (4, 1))
        self.assertTrue(black.is_harvester)
        self.assertTrue(white.is_harvester)
        black._reset()
        white._reset()
        self.assertEqual(black.current_pos, (1, 1))
        self.assertTrue(black.is_destroyer)
        self.assertEqual(white.current_pos, (6, 6))
        self.assertTrue(white.is_destroyer)

    def test_json_serialization(self):
        black = Bot(0, (1, 1), 0, (0, 3))
        white = Bot(1, (6, 6), 1, (3, 6), current_pos = (1, 1))

        black_json = json_converter.dumps(black)
        white_json = json_converter.dumps(white)

        black_json_target = {'__id__': 'pelita.datamodel.Bot',
                             '__value__': {'current_pos': [1, 1],
                                           'homezone': [0, 3],
                                           'index': 0,
                                           'initial_pos': [1, 1],
                                           'team_index': 0,
                                           'noisy': False}}

        white_json_target = {'__id__': 'pelita.datamodel.Bot',
                             '__value__': {'current_pos': [1, 1],
                                           'homezone': [3, 6],
                                           'index': 1,
                                           'initial_pos': [6, 6],
                                           'team_index': 1,
                                           'noisy': False}}

        self.assertEqual(json.loads(black_json), black_json_target)
        self.assertEqual(json.loads(white_json), white_json_target)

        self.assertEqual(json_converter.loads(black_json), black)
        self.assertEqual(json_converter.loads(white_json), white)

class TestTeam(unittest.TestCase):

    def test_init(self):
        team_black = Team(0, 'black', (0, 2))
        team_white = Team(1, 'white', (3, 6), score=5, bots=[1, 3, 5])

        self.assertEqual(team_black.index, 0)
        self.assertEqual(team_black.name, 'black')
        self.assertEqual(team_black.score, 0)
        self.assertEqual(team_black.zone, (0, 2))
        self.assertEqual(team_black.bots, [])

        self.assertEqual(team_white.index, 1)
        self.assertEqual(team_white.name, 'white')
        self.assertEqual(team_white.score, 5)
        self.assertEqual(team_white.zone, (3, 6))
        self.assertEqual(team_white.bots, [1, 3, 5])

    def test_methods(self):
        team_black = Team(0, 'black', (0, 2))
        team_white = Team(1, 'white', (3, 6), score=5, bots=[1, 3, 5])

        team_black._add_bot(0)
        self.assertEqual(team_black.bots, [0])
        team_white._add_bot(7)
        self.assertEqual(team_white.bots, [1, 3, 5, 7])
        self.assertTrue(team_black.in_zone((1, 5)))
        self.assertFalse(team_black.in_zone((5, 1)))
        self.assertTrue(team_white.in_zone((5, 1)))
        self.assertFalse(team_white.in_zone((1, 5)))
        team_black._score_point()
        self.assertEqual(team_black.score, 1)
        team_white._score_point()
        self.assertEqual(team_white.score, 6)

    def test_str_repr_eq(self):
        team_black = Team(0, 'black', (0, 2))
        team_white = Team(1, 'white', (3, 6), score=5, bots=[1, 3, 5])
        team_black2 = Team(0, 'black', (0, 2))
        self.assertEqual(team_black, team_black)
        self.assertEqual(team_black, team_black2)
        self.assertNotEqual(team_black, team_white)
        self.assertEqual(team_black.__str__(), 'black')
        self.assertEqual(team_white.__str__(), 'white')
        team_black3 = eval(repr(team_black))
        self.assertEqual(team_black, team_black3)
        team_white2 = eval(repr(team_white))
        self.assertEqual(team_white, team_white2)

    def test_json_serialization(self):
        team_black = Team(0, 'black', (0, 2))
        team_white = Team(1, 'white', (3, 6), score=5, bots=[1, 3, 5])

        team_black_json = json_converter.dumps(team_black)
        team_white_json = json_converter.dumps(team_white)

        team_black_json_target = {"__id__": "pelita.datamodel.Team",
                                  "__value__": {"index": 0,
                                                "bots": [],
                                                "score": 0,
                                                "name": "black",
                                                "zone": [0, 2]}}

        team_white_json_target = {"__id__": "pelita.datamodel.Team",
                                  "__value__": {"index": 1,
                                                "bots": [1, 3, 5],
                                                "score": 5,
                                                "name": "white",
                                                "zone": [3, 6]}}

        self.assertEqual(json.loads(team_black_json), team_black_json_target)
        self.assertEqual(json.loads(team_white_json), team_white_json_target)

        self.assertEqual(json_converter.loads(team_black_json), team_black)
        self.assertEqual(json_converter.loads(team_white_json), team_white)


class TestMazeComponents(unittest.TestCase):

    def test_init_str_eq_repr(self):
        wall = Wall
        wall2 = Wall
        free = Free
        free2 = Free
        food = Food
        food2 = Food
        self.assertEqual(wall, wall2)
        self.assertNotEqual(wall, free)
        self.assertNotEqual(wall, food)
        self.assertEqual(free, free2)
        self.assertNotEqual(free, wall)
        self.assertNotEqual(free, food)
        self.assertEqual(food, food2)
        self.assertNotEqual(food, wall)
        self.assertNotEqual(food, free)
        self.assertEqual(str(wall), '#')
        self.assertEqual(str(free), ' ')
        self.assertEqual(str(food), '.')
        wall3 = eval(repr(wall))
        free3 = eval(repr(free))
        food3 = eval(repr(food))
        self.assertEqual(wall, wall3)
        self.assertEqual(free, free3)
        self.assertEqual(food, food3)


class TestMaze(unittest.TestCase):

    def test_init(self):
        # check we get errors with wrong stuff
        self.assertRaises(TypeError, Maze, 1, 1, data=[1])
        self.assertRaises(ValueError, Maze, 1, 1, data=["", ""])

    def test_in(self):
        maze = Maze(2, 1, data=[Wall + Free, Food + Wall])
        self.assertEqual(Wall in maze[0, 0], True)
        self.assertEqual(Free in maze[0, 0], True)
        self.assertEqual(Food in maze[1, 0], True)
        self.assertEqual(Wall in maze[1, 0], True)

        self.assertEqual(Food in maze[0, 0], False)
        self.assertEqual(Free in maze[1, 0], False)

    def test_get_at(self):
        maze = Maze(2, 1, data=[Wall + Free, Food + Wall])
        self.assertEqual(maze.get_at(Wall, (0, 0)), [Wall])
        self.assertEqual(maze.get_at(Free, (0, 0)), [Free])
        self.assertEqual(maze.get_at(Food, (1, 0)), [Food])
        self.assertEqual(maze.get_at(Wall, (1, 0)), [Wall])

        self.assertEqual(maze.get_at(Food, (0, 0)), [])
        self.assertEqual(maze.get_at(Free, (1, 0)), [])

    def test_remove_at(self):
        maze = Maze(2, 1, data=["#", " ."])
        maze.remove_at(Wall, (0, 0))
        self.assertEqual(list(maze[0, 0]), [])

        maze = Maze(2, 1, data=["#", " ."])
        self.assertRaises(ValueError, maze.remove_at, Free, (0, 0))

        maze = Maze(2, 1, data=["#", " ."])
        maze.remove_at(Free, (1, 0))
        self.assertEqual(list(maze[1, 0]), [Food])
        maze.remove_at(Food, (1, 0))
        self.assertEqual(list(maze[1, 0]), [])

    def test_pos_of(self):
        maze = Maze(2, 1, data=["#", " ."])
        self.assertEqual([(0,0)], maze.pos_of(Wall))
        self.assertEqual([(1,0)], maze.pos_of(Food))
        test_layout3 = (
        """ ##################
            # #.  .  # .     #
            # #####    ##### #
            #     . #  .  .# #
            ################## """)
        data = [l.strip() for l in test_layout3.split('\n')]
        data = reduce(lambda x,y: x + y, data)
        data = [d for d in data]
        maze = Maze(18, 5, data=data)
        walls = [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (5, 0), (6, 0), (7, 0), (8,
            0), (9, 0), (10, 0), (11, 0), (12, 0), (13, 0), (14, 0), (15, 0),
            (16, 0), (17, 0), (0, 1), (2, 1), (9, 1), (17, 1), (0, 2), (2, 2),
            (3, 2), (4, 2), (5, 2), (6, 2), (11, 2), (12, 2), (13, 2), (14, 2),
            (15, 2), (17, 2), (0, 3), (8, 3), (15, 3), (17, 3), (0, 4), (1, 4),
            (2, 4), (3, 4), (4, 4), (5, 4), (6, 4), (7, 4), (8, 4), (9, 4),
            (10, 4), (11, 4), (12, 4), (13, 4), (14, 4), (15, 4), (16, 4), (17,
                4)]
        foods = [(3, 1), (6, 1), (11, 1), (6, 3), (11, 3), (14, 3)]
        self.assertEqual(walls, maze.pos_of(Wall))
        self.assertEqual(foods, maze.pos_of(Food))

    def test_positions(self):
        maze = Maze(5, 5)
        self.assertEqual([(x, y) for y in range(5) for x in range(5)],
                maze.positions)

    def test_json(self):
        maze = Maze(2, 1, data=["#", " ."])
        maze_json = json_converter.dumps(maze)
        self.assertEqual(json_converter.loads(maze_json), maze)

    def test_eq_repr(self):
        maze = Maze(2, 1, data=["#", " ."])
        self.assertEqual(maze, eval(repr(maze)))

    def test_is_always_sorted_and_unique(self):
        maze_1 = Maze(2, 1, data=["#", " ."])
        maze_2 = Maze(2, 1, data=["#", ". "])
        self.assertEqual(maze_1, maze_2)

        maze_1[0,0] = "abcd"
        maze_1[1,0] = "bcda"
        self.assertEqual(maze_1[0,0], maze_1[1,0])
        self.assertEqual(maze_1[0,0], "abcd")
        self.assertEqual(maze_1[1,0], "abcd")


class TestCTFUniverse(unittest.TestCase):

    def test_factory(self):
        test_layout3 = (
        """ ##################
            #0#.  .  # .     #
            #1#####    #####2#
            #     . #  .  .#3#
            ################## """)
        universe = create_CTFUniverse(test_layout3, 4)
        # this checks that the methods extracts the food, and the initial
        # positions from the raw layout
        target_mesh = Mesh(18, 5, data = list('################### #.  .  # .     #'+\
                '# #####    ##### ##     . #  .  .# ###################'))
        target_mesh = create_maze(target_mesh)
        self.assertEqual(target_mesh, universe.maze)
        target_food_list = [(3, 1), (6, 1), (11, 1), (6, 3), (11, 3), (14, 3),  ]
        self.assertEqual(target_food_list, universe.food_list)
        team_black_food = [(3, 1), (6, 1), (6, 3)]
        team_white_food = [(11, 1), (11, 3), (14, 3)]
        self.assertEqual(universe.team_food(0), team_black_food)
        self.assertEqual(universe.enemy_food(0), team_white_food)
        self.assertEqual(universe.team_food(1), team_white_food)
        self.assertEqual(universe.enemy_food(1), team_black_food)

        self.assertEqual([b.initial_pos for b in universe.bots],
                [(1, 1), (1, 2), (16, 2), (16, 3)])

        self.assertEqual([universe.bots[0]], universe.other_team_bots(2))
        self.assertEqual([universe.bots[1]], universe.other_team_bots(3))
        self.assertEqual([universe.bots[2]], universe.other_team_bots(0))
        self.assertEqual([universe.bots[3]], universe.other_team_bots(1))

        self.assertEqual([universe.bots[i] for i in 0,2], universe.team_bots(0))
        self.assertEqual([universe.bots[i] for i in 0,2], universe.enemy_bots(1))
        self.assertEqual([universe.bots[i] for i in 1,3], universe.team_bots(1))
        self.assertEqual([universe.bots[i] for i in 1,3], universe.enemy_bots(0))

        self.assertEqual(universe.enemy_team(0), universe.teams[1])
        self.assertEqual(universe.enemy_team(1), universe.teams[0])

        self.assertEqual([(8, 1), (8, 2)], universe.team_border(0))
        self.assertEqual([(9, 2), (9, 3)], universe.team_border(1))

        odd_layout = (
            """ #####
                #0 1#
                ##### """)
        self.assertRaises(UniverseException, create_CTFUniverse, odd_layout, 2)

        odd_bots = (
            """ ####
                #01#
                #2 #
                #### """)
        self.assertRaises(UniverseException, create_CTFUniverse, odd_bots, 3)

        universe = create_CTFUniverse(test_layout3, 4, team_names=['orange', 'purple'])
        self.assertEqual(universe.teams[0].name, 'orange')
        self.assertEqual(universe.teams[1].name, 'purple')

    def test_neighbourhood(self):
        test_layout = (
            """ ######
                #    #
                #    #
                #    #
                ###### """)
        universe = create_CTFUniverse(test_layout, 0)
        current_position = (2, 2)
        new = universe.neighbourhood(current_position)
        target = { north : (2, 1),
                    south : (2, 3),
                    west  : (1, 2),
                    east  : (3, 2),
                    stop  : (2, 2) }
        self.assertEqual(target, new)

    def test_repr_eq(self):
        test_layout3 = (
        """ ##################
            #0#.  .  # .     #
            #1#####    #####2#
            #     . #  .  .#3#
            ################## """)
        universe = create_CTFUniverse(test_layout3, 4)

        test_layout3_2 = (
        """ ##################
            #0#.  .  # .     #
            #1#####    #####2#
            #     . #  .  .#3#
            ################## """)
        universe2 = create_CTFUniverse(test_layout3_2, 4)

        self.assertEqual(universe, universe2)
        self.assertEqual(universe, eval(repr(universe)))
        self.assertFalse(universe != eval(repr(universe)))

    def test_copy(self):
        test_layout3 = (
        """ ##################
            #0#.  .  # .     #
            #1#####    #####2#
            #     . #  .  .#3#
            ################## """)
        universe = create_CTFUniverse(test_layout3, 4)
        uni_copy = universe.copy()
        self.assertEqual(universe, uni_copy)
        # this is just a smoke test for the most volatile aspect of
        # of copying the universe
        for food_pos in universe.food_list:
            universe.maze.remove_at(Food, food_pos)
        self.assertNotEqual(universe, uni_copy)
        self.assertEqual(universe, universe.copy())

    def test_str_compact_str(self):
        test_layout3 = (
        """ ##################
            #0#.  .  # .     #
            #1#####    #####2#
            #     . #  .  .#3#
            ################## """)
        universe = create_CTFUniverse(test_layout3, 4)
        compact_str_target = (
            '##################\n'
            '#0#.  .  # .     #\n'
            '#1#####    #####2#\n'
            '#     . #  .  .#3#\n'
            '##################\n')
        self.assertEqual(compact_str_target, universe.compact_str)
        str_target = (
        "['#', '#', '#', '#', '#', '#', '#', '#', '#', '#', '#', '#', '#', '#', '#', '#', '#', '#']\n"
        "['#', '0', '#', '.', ' ', ' ', '.', ' ', ' ', '#', ' ', '.', ' ', ' ', ' ', ' ', ' ', '#']\n"
        "['#', '1', '#', '#', '#', '#', '#', ' ', ' ', ' ', ' ', '#', '#', '#', '#', '#', '2', '#']\n"
        "['#', ' ', ' ', ' ', ' ', ' ', '.', ' ', '#', ' ', ' ', '.', ' ', ' ', '.', '#', '3', '#']\n"
        "['#', '#', '#', '#', '#', '#', '#', '#', '#', '#', '#', '#', '#', '#', '#', '#', '#', '#']\n")
        self.assertEqual(str_target, str(universe))

        pretty_target = (
            "##################\n"
            "#0#.  .  # .     #\n"
            "#1#####    #####2#\n"
            "#     . #  .  .#3#\n"
            "##################\n"
            "Team(0, 'black', (0, 8), score=0, bots=[0, 2])\n"
            "\tBot(0, (1, 1), 0, (0, 8) , current_pos=(1, 1), noisy=False)\n"
            "\tBot(2, (16, 2), 0, (0, 8) , current_pos=(16, 2), noisy=False)\n"
            "Team(1, 'white', (9, 17), score=0, bots=[1, 3])\n"
            "\tBot(1, (1, 2), 1, (9, 17) , current_pos=(1, 2), noisy=False)\n"
            "\tBot(3, (16, 3), 1, (9, 17) , current_pos=(16, 3), noisy=False)\n")
        self.assertEqual(pretty_target, universe.pretty)

    def test_bot_teams(self):

        test_layout4 = (
            """ ######
                #0  1#
                #2  3#
                ###### """)
        universe = create_CTFUniverse(test_layout4, 4)

        team_black = Team(0, 'black', (0, 2), bots=[0, 2])
        team_white = Team(1, 'white', (3, 5), bots=[1, 3])

        self.assertEqual(universe.teams[0], team_black)
        self.assertEqual(universe.teams[1], team_white)

        self.assertEqual(universe.bots[0].team_index, 0)
        self.assertEqual(universe.bots[2].team_index, 0)
        self.assertEqual(universe.bots[1].team_index, 1)
        self.assertEqual(universe.bots[3].team_index, 1)

        self.assertTrue(universe.bots[0].in_own_zone)
        self.assertTrue(universe.bots[1].in_own_zone)
        self.assertTrue(universe.bots[2].in_own_zone)
        self.assertTrue(universe.bots[3].in_own_zone)

        test_layout4 = (
            """ ######
                #1  0#
                #3  2#
                ###### """)
        universe = create_CTFUniverse(test_layout4, 4)

        self.assertFalse(universe.bots[0].in_own_zone)
        self.assertFalse(universe.bots[1].in_own_zone)
        self.assertFalse(universe.bots[2].in_own_zone)
        self.assertFalse(universe.bots[3].in_own_zone)

        test_layout4 = (
            """ ######
                #0 2 #
                # 1 3#
                ###### """)
        universe = create_CTFUniverse(test_layout4, 4)
        self.assertTrue(universe.bots[1].is_harvester)
        self.assertTrue(universe.bots[2].is_harvester)
        self.assertFalse(universe.bots[0].is_harvester)
        self.assertFalse(universe.bots[3].is_harvester)
        self.assertFalse(universe.bots[1].is_destroyer)
        self.assertFalse(universe.bots[2].is_destroyer)
        self.assertTrue(universe.bots[0].is_destroyer)
        self.assertTrue(universe.bots[3].is_destroyer)

    def test_json(self):
        test_layout3 = (
        """ ##################
            #0#.  .  # .     #
            #1#####    #####2#
            #     . #  .  .#3#
            ################## """)
        universe = create_CTFUniverse(test_layout3, 4)
        universe_json = json_converter.dumps(universe)
        self.assertEqual(json_converter.loads(universe_json), universe)

    def test_too_many_enemy_teams(self):
        test_layout3 = (
        """ ##################
            #0#.  .  # .     #
            #1#####    #####2#
            #     . #  .  .#3#
            ################## """)
        universe = create_CTFUniverse(test_layout3, 4)
        # cheating
        universe.teams.append(Team(2, "noname", ()))
        self.assertRaises(UniverseException, universe.enemy_team, 0)


class TestCTFUniverseRules(unittest.TestCase):

    def test_get_legal_moves(self):
        test_legal = (
            """ ######
                #  # #
                #   ##
                #    #
                ###### """)
        universe = create_CTFUniverse(test_legal, 0)
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

    def test_get_legal_moves_or_stop(self):
        test_legal = (
            """ ######
                #  # #
                #   ##
                #    #
                ###### """)
        universe = create_CTFUniverse(test_legal, 0)
        legal_moves_1_1 = universe.get_legal_moves_or_stop((1, 1))
        target = {east  : (2, 1),
                  south : (1, 2)}
        self.assertEqual(target, legal_moves_1_1)
        legal_moves_2_1 = universe.get_legal_moves_or_stop((2, 1))
        target = {west  : (1, 1),
                  south : (2, 2)}
        self.assertEqual(target, legal_moves_2_1)
        legal_moves_4_1 = universe.get_legal_moves_or_stop((4, 1))
        target = { stop : (4, 1)}
        self.assertEqual(target, legal_moves_4_1)
        legal_moves_1_2 = universe.get_legal_moves_or_stop((1, 2))
        target = {north : (1, 1),
                  east  : (2, 2),
                  south : (1, 3)}
        self.assertEqual(target, legal_moves_1_2)
        legal_moves_2_2 = universe.get_legal_moves_or_stop((2, 2))
        target = {north : (2, 1),
                  east  : (3, 2),
                  south : (2, 3),
                  west  : (1, 2)}
        self.assertEqual(target, legal_moves_2_2)
        legal_moves_3_2 = universe.get_legal_moves_or_stop((3, 2))
        target = {south : (3, 3),
                  west  : (2, 2)}
        self.assertEqual(target, legal_moves_3_2)
        legal_moves_1_3 = universe.get_legal_moves_or_stop((1, 3))
        target = {north : (1, 2),
                  east  : (2, 3)}
        self.assertEqual(target, legal_moves_1_3)
        legal_moves_2_3 = universe.get_legal_moves_or_stop((2, 3))
        target = {north : (2, 2),
                  east  : (3, 3),
                  west  : (1, 3)}
        self.assertEqual(target, legal_moves_2_3)
        # 3, 3 has the same options as 2, 3
        legal_moves_4_3 = universe.get_legal_moves_or_stop((4, 3))
        target = {west  : (3, 3)}
        self.assertEqual(target, legal_moves_4_3)

    def test_move_bot_exceptions(self):
        test_move_bot = (
            """ ######
                #  #0#
                # 3 ##
                #2  1#
                ###### """)
        universe = create_CTFUniverse(test_move_bot, 4)

        self.assertRaises(IllegalMoveException, universe.move_bot, 0, 'FOOBAR')
        self.assertRaises(IllegalMoveException, universe.move_bot, 0, (0, 2))

        self.assertRaises(IllegalMoveException, universe.move_bot, 0, north)
        self.assertRaises(IllegalMoveException, universe.move_bot, 0, west)
        self.assertRaises(IllegalMoveException, universe.move_bot, 0, south)
        self.assertRaises(IllegalMoveException, universe.move_bot, 0, east)

        self.assertRaises(IllegalMoveException, universe.move_bot, 1, north)
        self.assertRaises(IllegalMoveException, universe.move_bot, 1, east)
        self.assertRaises(IllegalMoveException, universe.move_bot, 1, south)

        self.assertRaises(IllegalMoveException, universe.move_bot, 2, west)
        self.assertRaises(IllegalMoveException, universe.move_bot, 2, south)

    def test_reset_bot_bot_positions(self):

        test_reset_bot = (
            """ ########
                #0     #
                #2    3#
                #     1#
                ######## """)
        number_bots = 4
        universe = create_CTFUniverse(test_reset_bot, number_bots)
        self.assertEqual(str(universe),
                str(Layout(test_reset_bot, layout_chars, number_bots).as_mesh()))
        self.assertEqual(universe.bot_positions,
                [(1, 1), (6, 3), (1, 2), (6, 2)])
        test_shuffle = (
            """ ########
                #   0 3#
                # 1    #
                # 2    #
                ######## """)
        universe.bots[0].current_pos = (4, 1)
        universe.bots[1].current_pos = (2, 2)
        universe.bots[2].current_pos = (2, 3)
        universe.bots[3].current_pos = (6, 1)
        self.assertEqual(universe.bot_positions,
                [(4, 1), (2, 2), (2, 3), (6, 1)])
        self.assertEqual(str(universe),
                str(Layout(test_shuffle, layout_chars, number_bots).as_mesh()))
        universe.bots[0]._reset()
        universe.bots[1]._reset()
        universe.bots[2]._reset()
        universe.bots[3]._reset()
        self.assertEqual(str(universe),
                str(Layout(test_reset_bot, layout_chars, number_bots).as_mesh()))
        self.assertEqual(universe.bot_positions,
                [(1, 1), (6, 3), (1, 2), (6, 2)])

    def test_one(self):

        number_bots = 2

        # The problem here is that the layout does not allow us to specify a
        # different inital position and current position. When testing universe
        # equality by comparing its string representation, this does not matter.
        # But if we want to compare using the __eq__ method, but specify the
        # target as ascii encoded maze/layout we need to convert the layout to a
        # CTFUniverse and then modify the initial positions. For this we define
        # a closure here to quickly generate a target universe to compare to.
        # Also we adapt the score, in case food has been eaten

        def create_TestUniverse(layout, black_score=0, white_score=0):
            initial_pos = [(1, 1), (4, 2)]
            universe = create_CTFUniverse(layout, number_bots)
            universe.teams[0].score = black_score
            universe.teams[1].score = white_score
            for i, pos in enumerate(initial_pos):
                universe.bots[i].initial_pos = pos
            if not Food in universe.maze[1, 2]:
                universe.teams[1]._score_point()
            if not Food in universe.maze[3, 1]:
                universe.teams[0]._score_point()
            return universe

        test_start = (
            """ ######
                #0 . #
                #.  1#
                ###### """)
        universe = create_CTFUniverse(test_start, number_bots)
        game_state = universe.move_bot(1, west)
        test_first_move = (
            """ ######
                #0 . #
                #. 1 #
                ###### """)
        self.assertEqual(create_TestUniverse(test_first_move), universe)
        self.assertEqual(game_state["bot_moved"][0], {"bot_id": 1, "old_pos": (4, 2), "new_pos": (3, 2)})
        test_second_move = (
            """ ######
                #0 . #
                #.1  #
                ###### """)
        game_state = universe.move_bot(1, west)
        self.assertEqual(create_TestUniverse(test_second_move), universe)
        self.assertEqual(game_state["bot_moved"][0], {"bot_id": 1, "old_pos": (3, 2), "new_pos": (2, 2)})
        test_eat_food = (
            """ ######
                #0 . #
                #1   #
                ###### """)
        self.assertEqual(universe.food_list, [(3, 1), (1, 2)])
        game_state = universe.move_bot(1, west)
        self.assertEqual(create_TestUniverse(test_eat_food), universe)
        self.assertEqual(universe.food_list, [(3, 1)])
        self.assertEqual(universe.teams[1].score, 1)
        self.assertEqual(game_state, {
            "bot_moved": [{"bot_id": 1, "old_pos": (2, 2), "new_pos": (1, 2)}],
            "food_eaten": [{"bot_id": 1, "food_pos": (1,2)}],
            "bot_destroyed": []
            })

        test_destruction = (
            """ ######
                #  . #
                #0  1#
                ###### """)
        game_state = universe.move_bot(0, south)
        self.assertEqual(create_TestUniverse(test_destruction,
            black_score=KILLPOINTS), universe)
        self.assertEqual(game_state, {
            "bot_moved": [{"bot_id": 0, "old_pos": (1, 1), "new_pos": (1, 2)}, {'old_pos': (1, 2), 'new_pos': (1, 2), 'bot_id': 0}],
            "food_eaten": [],
            "bot_destroyed": [{"bot_id": 1, "destroyed_by": 0}]
        })

        test_black_score = (
            """ ######
                #  0 #
                #   1#
                ###### """)
        universe.move_bot(0, north)
        universe.move_bot(0, east)
        game_state = universe.move_bot(0, east)
        self.assertEqual(create_TestUniverse(test_black_score,
            black_score=KILLPOINTS), universe)
        self.assertEqual(universe.food_list, [])
        self.assertEqual(universe.teams[0].score, KILLPOINTS+1)
        self.assertEqual(game_state, {
            "bot_moved": [{"bot_id": 0, "old_pos": (2, 1), "new_pos": (3, 1)}],
            "food_eaten": [{"bot_id": 0, "food_pos": (3, 1)}],
            "bot_destroyed": []
        })
        test_bot_suicide = (
            """ ######
                #0   #
                #   1#
                ###### """)
        universe.move_bot(0, east)
        game_state = universe.move_bot(0, south)
        self.assertEqual(create_TestUniverse(test_bot_suicide,
            black_score=KILLPOINTS, white_score=KILLPOINTS), universe)
        self.assertEqual(game_state, {
            "bot_moved": [{"bot_id": 0, "old_pos": (4, 1), "new_pos": (4, 2)}, {'old_pos': (4, 2), 'new_pos': (1, 1), 'bot_id': 0}],
            "food_eaten": [],
            "bot_destroyed": [{"bot_id": 0, "destroyed_by": 1}]
        })

    def test_no_eat_own_food(self):
        test_start = (
            """ ######
                #0 . #
                #.  1#
                ###### """)
        number_bots = 2
        universe = create_CTFUniverse(test_start, number_bots)
        universe.move_bot(1, north)
        game_state = universe.move_bot(1, west)
        self.assertEqual(universe.food_list, [(3, 1), (1, 2)])
        self.assertEqual(game_state["bot_moved"][0], {"bot_id": 1, "old_pos": (4, 1), "new_pos": (3, 1)})

    def test_suicide_win(self):
        test = (
            """ ######
                #0 .1#
                #.   #
                ###### """)
        universe = create_CTFUniverse(test, 2)
        universe.move_bot(0, east)
        universe.move_bot(1, west)
        game_state = universe.move_bot(0, east)
        target = {
            "bot_moved": [{"bot_id": 0, "old_pos": (2, 1), "new_pos": (3, 1)}, {"bot_id": 0, "old_pos": (3, 1), "new_pos": (1, 1)}],
            "food_eaten": [{"bot_id": 0, "food_pos": (3, 1)}],
            "bot_destroyed": [{"bot_id": 0, "destroyed_by": 1}]
        }
        self.assertEqual(game_state, target)

if __name__ == '__main__':
    unittest.main()

