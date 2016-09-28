import pytest
import unittest

from pelita.datamodel import *
from pelita.layout import Layout

# the legal chars for a basic CTFUniverse
# see also: CTFUniverse.create factory.
layout_chars = maze_components

class TestStaticmethods:
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
        assert target == initial_pos
        # also test the side-effect of initial_positions()
        target = Mesh(7, 5, data =list('########     ##     ##     ########'))
        assert target == mesh

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
        assert target == initial_pos
        # also test the side-effect of initial_positions()
        target = Mesh(18, 5, data = list('################### #      #       #'+\
                '# #####    ##### ##       #      # ###################'))
        assert target == mesh


class TestBot:
    def test_init_in_own_zone_is_harvester(self):
        bot = Bot(0, (1, 1), 0, (0, 3))
        assert bot.index == 0
        assert bot.initial_pos == (1, 1)
        assert bot.current_pos == (1, 1)
        assert bot.team_index == 0
        assert bot.homezone == (0, 3)
        assert bot.is_destroyer
        assert not bot.is_harvester
        assert bot.in_own_zone

        bot = Bot(1, (6, 6), 1, (3, 6), current_pos = (1, 1))
        assert bot.index == 1
        assert bot.initial_pos == (6, 6)
        assert bot.current_pos == (1, 1)
        assert bot.team_index == 1
        assert bot.homezone == (3, 6)
        assert not bot.is_destroyer
        assert bot.is_harvester
        assert not bot.in_own_zone

    def test_eq_repr_cmp(self):
        black = Bot(0, (1, 1), 0, (0, 3))
        black2 = Bot(0, (1, 1), 0, (0, 3))
        white = Bot(1, (6, 6), 1, (3, 6), current_pos = (1, 1))
        assert black != white
        assert black == black2
        black3 = eval(repr(black))
        assert black == black3

    def test_move_to_initial(self):
        black = Bot(0, (1, 1), 0, (0, 3))
        white = Bot(1, (6, 6), 1, (3, 6), current_pos = (1, 1))
        assert black.is_destroyer
        black.current_pos = (4, 1)
        assert black.current_pos == (4, 1)
        assert black.is_harvester
        assert white.is_harvester
        black._to_initial()
        white._to_initial()
        assert black.current_pos == (1, 1)
        assert black.is_destroyer
        assert white.current_pos == (6, 6)
        assert white.is_destroyer


class TestTeam:

    def test_init(self):
        team_black = Team(0, (0, 2))
        team_white = Team(1, (3, 6), score=5)

        assert team_black.index == 0
        assert team_black.score == 0
        assert team_black.zone == (0, 2)

        assert team_white.index == 1
        assert team_white.score == 5
        assert team_white.zone == (3, 6)

    def test_methods(self):
        team_black = Team(0, (0, 2))
        team_white = Team(1, (3, 6), score=5)

        assert team_black.in_zone((1, 5))
        assert not team_black.in_zone((5, 1))
        assert team_white.in_zone((5, 1))
        assert not team_white.in_zone((1, 5))

    def test_str_repr_eq(self):
        team_black = Team(0, (0, 2))
        team_white = Team(1, (3, 6), score=5)
        team_black2 = Team(0, (0, 2))
        assert team_black == team_black
        assert team_black == team_black2
        assert team_black != team_white
        assert team_black.__str__() == "Team(0, (0, 2), score=0)"
        assert team_white.__str__() == "Team(1, (3, 6), score=5)"
        team_black3 = eval(repr(team_black))
        assert team_black == team_black3
        team_white2 = eval(repr(team_white))
        assert team_white == team_white2


class TestMazeComponents:

    def test_init_str_eq_repr(self):
        wall = Wall
        wall2 = Wall
        free = Free
        free2 = Free
        food = Food
        food2 = Food
        assert wall == wall2
        assert wall != free
        assert wall != food
        assert free == free2
        assert free != wall
        assert free != food
        assert food == food2
        assert food != wall
        assert food != free
        assert str(wall) == '#'
        assert str(free) == ' '
        assert str(food) == '.'
        wall3 = eval(repr(wall))
        free3 = eval(repr(free))
        food3 = eval(repr(food))
        assert wall == wall3
        assert free == free3
        assert food == food3


class TestMaze:
    def test_init(self):
        # check we get errors with wrong stuff
        with pytest.raises(TypeError):
            Maze(1, 1, data=[1])
        with pytest.raises(TypeError):
            Maze(1, 1, data=[""])
        with pytest.raises(ValueError):
            Maze(1, 1, data=[True, False])

    def test_positions(self):
        maze = Maze(5, 5)
        assert [(x, y) for y in range(5) for x in range(5)] == \
                         list(maze.positions)

    def test_eq_repr(self):
        maze = Maze(2, 1, data=[True, False])
        assert maze == eval(repr(maze))


class TestCTFUniverse:

    def test_factory(self):
        test_layout3 = (
        """ ##################
            #0#.  .  # .     #
            #1#####    #####2#
            #     . #  .  .#3#
            ################## """)
        universe = CTFUniverse.create(test_layout3, 4)
        # this checks that the methods extracts the food, and the initial
        # positions from the raw layout
        target_mesh = Mesh(18, 5, data = list('################### #.  .  # .     #'+\
                '# #####    ##### ##     . #  .  .# ###################'))
        target_mesh, target_food = create_maze(target_mesh)
        assert target_mesh == universe.maze
        target_food_list = [(3, 1), (6, 1), (11, 1), (6, 3), (11, 3), (14, 3),  ]
        unittest.TestCase().assertCountEqual(target_food_list, universe.food_list)
        team_black_food = [(3, 1), (6, 1), (6, 3)]
        team_white_food = [(11, 1), (11, 3), (14, 3)]
        unittest.TestCase().assertCountEqual(universe.team_food(0), team_black_food)
        unittest.TestCase().assertCountEqual(universe.enemy_food(0), team_white_food)
        unittest.TestCase().assertCountEqual(universe.team_food(1), team_white_food)
        unittest.TestCase().assertCountEqual(universe.enemy_food(1), team_black_food)

        assert [b.initial_pos for b in universe.bots] == \
                [(1, 1), (1, 2), (16, 2), (16, 3)]

        assert [universe.bots[0]] == universe.other_team_bots(2)
        assert [universe.bots[1]] == universe.other_team_bots(3)
        assert [universe.bots[2]] == universe.other_team_bots(0)
        assert [universe.bots[3]] == universe.other_team_bots(1)

        assert [universe.bots[i] for i in (0,2)] == universe.team_bots(0)
        assert [universe.bots[i] for i in (0,2)] == universe.enemy_bots(1)
        assert [universe.bots[i] for i in (1,3)] == universe.team_bots(1)
        assert [universe.bots[i] for i in (1,3)] == universe.enemy_bots(0)

        assert universe.enemy_team(0) == universe.teams[1]
        assert universe.enemy_team(1) == universe.teams[0]

        assert [(8, 1), (8, 2)] == universe.team_border(0)
        assert [(9, 2), (9, 3)] == universe.team_border(1)

        odd_layout = (
            """ #####
                #0 1#
                ##### """)
        with pytest.raises(UniverseException):
            CTFUniverse.create(odd_layout, 2)

        odd_bots = (
            """ ####
                #01#
                #2 #
                #### """)
        with pytest.raises(UniverseException):
            CTFUniverse.create(odd_bots, 3)

    def test_neighbourhood(self):
        test_layout = (
            """ ######
                #    #
                #    #
                #    #
                ###### """)
        universe = CTFUniverse.create(test_layout, 0)
        current_position = (2, 2)
        new = universe.neighbourhood(current_position)
        target = { north : (2, 1),
                    south : (2, 3),
                    west  : (1, 2),
                    east  : (3, 2),
                    stop  : (2, 2) }
        assert target == new
        current_position = (1, 1)
        new = universe.neighbourhood(current_position)
        target = { north : (1, 0),
                    south : (1, 2),
                    west  : (0, 1),
                    east  : (2, 1),
                    stop  : (1, 1) }
        assert target == new
        current_position = (0, 0)
        new = universe.neighbourhood(current_position)
        target = {  south : (0, 1),
                    east  : (1, 0),
                    stop  : (0, 0) }
        assert target == new
        current_position = (5, 4)
        new = universe.neighbourhood(current_position)
        target = { west: (4, 4),
                   north: (5, 3),
                   stop: (5, 4) }
        assert target == new


    def test_repr_eq(self):
        test_layout3 = (
        """ ##################
            #0#.  .  # .     #
            #1#####    #####2#
            #     . #  .  .#3#
            ################## """)
        universe = CTFUniverse.create(test_layout3, 4)

        test_layout3_2 = (
        """ ##################
            #0#.  .  # .     #
            #1#####    #####2#
            #     . #  .  .#3#
            ################## """)
        universe2 = CTFUniverse.create(test_layout3_2, 4)

        assert universe == universe2
        assert universe == eval(repr(universe))

    def test_copy(self):
        test_layout3 = (
        """ ##################
            #0#.  .  # .     #
            #1#####    #####2#
            #     . #  .  .#3#
            ################## """)
        universe = CTFUniverse.create(test_layout3, 4)
        uni_copy = universe.copy()
        assert universe == uni_copy
        # this is just a smoke test for the most volatile aspect of
        # of copying the universe
        universe.food.pop()
        assert universe != uni_copy
        assert universe == universe.copy()

    def test_str_compact_str(self):
        test_layout3 = (
        """ ##################
            #0#.  .  # .     #
            #1#####    #####2#
            #     . #  .  .#3#
            ################## """)
        universe = CTFUniverse.create(test_layout3, 4)
        compact_str_target = (
            '##################\n'
            '#0#.  .  # .     #\n'
            '#1#####    #####2#\n'
            '#     . #  .  .#3#\n'
            '##################\n')
        assert compact_str_target == universe.compact_str
        str_target = (
        "['#', '#', '#', '#', '#', '#', '#', '#', '#', '#', '#', '#', '#', '#', '#', '#', '#', '#']\n"
        "['#', '0', '#', '.', ' ', ' ', '.', ' ', ' ', '#', ' ', '.', ' ', ' ', ' ', ' ', ' ', '#']\n"
        "['#', '1', '#', '#', '#', '#', '#', ' ', ' ', ' ', ' ', '#', '#', '#', '#', '#', '2', '#']\n"
        "['#', ' ', ' ', ' ', ' ', ' ', '.', ' ', '#', ' ', ' ', '.', ' ', ' ', '.', '#', '3', '#']\n"
        "['#', '#', '#', '#', '#', '#', '#', '#', '#', '#', '#', '#', '#', '#', '#', '#', '#', '#']\n")
        assert str_target == str(universe)

        pretty_target = (
            "##################\n"
            "#0#.  .  # .     #\n"
            "#1#####    #####2#\n"
            "#     . #  .  .#3#\n"
            "##################\n"
            "Team(0, (0, 8), score=0)\n"
            "\tBot(0, (1, 1), 0, (0, 8) , current_pos=(1, 1), noisy=False)\n"
            "\tBot(2, (16, 2), 0, (0, 8) , current_pos=(16, 2), noisy=False)\n"
            "Team(1, (9, 17), score=0)\n"
            "\tBot(1, (1, 2), 1, (9, 17) , current_pos=(1, 2), noisy=False)\n"
            "\tBot(3, (16, 3), 1, (9, 17) , current_pos=(16, 3), noisy=False)\n")
        assert pretty_target == universe.pretty

    def test_bot_teams(self):

        test_layout4 = (
            """ ######
                #0  1#
                #2  3#
                ###### """)
        universe = CTFUniverse.create(test_layout4, 4)

        team_black = Team(0, (0, 2))
        team_white = Team(1, (3, 5))

        assert universe.teams[0] == team_black
        assert universe.teams[1] == team_white

        assert universe.bots[0].team_index == 0
        assert universe.bots[2].team_index == 0
        assert universe.bots[1].team_index == 1
        assert universe.bots[3].team_index == 1

        assert universe.bots[0].in_own_zone
        assert universe.bots[1].in_own_zone
        assert universe.bots[2].in_own_zone
        assert universe.bots[3].in_own_zone

        test_layout4 = (
            """ ######
                #1  0#
                #3  2#
                ###### """)
        universe = CTFUniverse.create(test_layout4, 4)

        assert not universe.bots[0].in_own_zone
        assert not universe.bots[1].in_own_zone
        assert not universe.bots[2].in_own_zone
        assert not universe.bots[3].in_own_zone

        test_layout4 = (
            """ ######
                #0 2 #
                # 1 3#
                ###### """)
        universe = CTFUniverse.create(test_layout4, 4)
        assert universe.bots[1].is_harvester
        assert universe.bots[2].is_harvester
        assert not universe.bots[0].is_harvester
        assert not universe.bots[3].is_harvester
        assert not universe.bots[1].is_destroyer
        assert not universe.bots[2].is_destroyer
        assert universe.bots[0].is_destroyer
        assert universe.bots[3].is_destroyer

    def test_json(self):
        test_layout3 = (
        """ ##################
            #0#.  .  # .     #
            #1#####    #####2#
            #     . #  .  .#3#
            ################## """)
        universe = CTFUniverse.create(test_layout3, 4)
        maze_data = universe.maze._data

        universe_json = {
                "maze": {
                    "height": 5,
                    "width": 18,
                    "data": maze_data[:],
                },
                "food": [(6, 1), (3, 1), (11, 3), (6, 3), (11, 1), (14, 3)],
                "teams": [
                    {'score': 0, 'zone': (0, 8), 'index': 0},
                    {'score': 0, 'zone': (9, 17), 'index': 1}
                ],
                "bots": [
                    {'team_index': 0, 'homezone': (0, 8), 'noisy': False,
                        'current_pos': (1, 1), 'index': 0, 'initial_pos': (1, 1)},
                    {'team_index': 1, 'homezone': (9, 17), 'noisy': False,
                        'current_pos': (1, 2), 'index': 1, 'initial_pos': (1, 2)},
                    {'team_index': 0, 'homezone': (0, 8), 'noisy': False,
                        'current_pos': (16, 2), 'index': 2, 'initial_pos': (16, 2)},
                    {'team_index': 1, 'homezone': (9, 17), 'noisy': False,
                        'current_pos': (16, 3), 'index': 3, 'initial_pos': (16, 3)}
                ]
            }

        universe_dict = universe._to_json_dict()
        # we don’t guarantee the order of the food items
        universe_dict["food"].sort()
        universe_json["food"].sort()

        assert universe_json == universe_dict

        universe2 = CTFUniverse._from_json_dict(universe_json)
        assert universe == universe2


    def test_too_many_enemy_teams(self):
        test_layout3 = (
        """ ##################
            #0#.  .  # .     #
            #1#####    #####2#
            #     . #  .  .#3#
            ################## """)
        universe = CTFUniverse.create(test_layout3, 4)
        # cheating
        universe.teams.append(Team(2, "noname", ()))
        with pytest.raises(UniverseException):
            universe.enemy_team(0)

    def test_reachable(self):
        test_layout = (
        """ ##################
            #0#.  .  # .1#   #
            #2#####    ##### #
            #     . #  .  .#3#
            ################## """)
        universe = CTFUniverse.create(test_layout, 4)
        reachable = [dict(universe.reachable([bot.initial_pos])) for bot in universe.bots]
        assert all(bot.initial_pos in reachable[i] for i, bot in enumerate(universe.bots))
        assert universe.bots[0].initial_pos in reachable[1]
        assert not (universe.bots[3].initial_pos in reachable[0])
        assert not (universe.bots[0].initial_pos in reachable[3])

class TestCTFUniverseRules:
    def test_legal_moves(self):
        test_legal = (
            """ ######
                #  # #
                #   ##
                #    #
                ###### """)
        universe = CTFUniverse.create(test_legal, 0)
        legal_moves_1_1 = universe.legal_moves((1, 1))
        target = {east  : (2, 1),
                  south : (1, 2),
                  stop  : (1, 1)}
        assert target == legal_moves_1_1
        legal_moves_2_1 = universe.legal_moves((2, 1))
        target = {west  : (1, 1),
                  south : (2, 2),
                  stop  : (2, 1)}
        assert target == legal_moves_2_1
        legal_moves_4_1 = universe.legal_moves((4, 1))
        target = { stop : (4, 1)}
        assert target == legal_moves_4_1
        legal_moves_1_2 = universe.legal_moves((1, 2))
        target = {north : (1, 1),
                  east  : (2, 2),
                  south : (1, 3),
                  stop  : (1, 2)}
        assert target == legal_moves_1_2
        legal_moves_2_2 = universe.legal_moves((2, 2))
        target = {north : (2, 1),
                  east  : (3, 2),
                  south : (2, 3),
                  west  : (1, 2),
                  stop  : (2, 2)}
        assert target == legal_moves_2_2
        legal_moves_3_2 = universe.legal_moves((3, 2))
        target = {south : (3, 3),
                  west  : (2, 2),
                  stop  : (3, 2)}
        assert target == legal_moves_3_2
        legal_moves_1_3 = universe.legal_moves((1, 3))
        target = {north : (1, 2),
                  east  : (2, 3),
                  stop  : (1, 3)}
        assert target == legal_moves_1_3
        legal_moves_2_3 = universe.legal_moves((2, 3))
        target = {north : (2, 2),
                  east  : (3, 3),
                  west  : (1, 3),
                  stop  : (2, 3)}
        assert target == legal_moves_2_3
        # 3, 3 has the same options as 2, 3
        legal_moves_4_3 = universe.legal_moves((4, 3))
        target = {west  : (3, 3),
                  stop  : (4, 3)}
        assert target == legal_moves_4_3

    def test_legal_moves_or_stop(self):
        test_legal = (
            """ ######
                #  # #
                #   ##
                #    #
                ###### """)
        universe = CTFUniverse.create(test_legal, 0)
        legal_moves_1_1 = universe.legal_moves_or_stop((1, 1))
        target = {east  : (2, 1),
                  south : (1, 2)}
        assert target == legal_moves_1_1
        legal_moves_2_1 = universe.legal_moves_or_stop((2, 1))
        target = {west  : (1, 1),
                  south : (2, 2)}
        assert target == legal_moves_2_1
        legal_moves_4_1 = universe.legal_moves_or_stop((4, 1))
        target = { stop : (4, 1)}
        assert target == legal_moves_4_1
        legal_moves_1_2 = universe.legal_moves_or_stop((1, 2))
        target = {north : (1, 1),
                  east  : (2, 2),
                  south : (1, 3)}
        assert target == legal_moves_1_2
        legal_moves_2_2 = universe.legal_moves_or_stop((2, 2))
        target = {north : (2, 1),
                  east  : (3, 2),
                  south : (2, 3),
                  west  : (1, 2)}
        assert target == legal_moves_2_2
        legal_moves_3_2 = universe.legal_moves_or_stop((3, 2))
        target = {south : (3, 3),
                  west  : (2, 2)}
        assert target == legal_moves_3_2
        legal_moves_1_3 = universe.legal_moves_or_stop((1, 3))
        target = {north : (1, 2),
                  east  : (2, 3)}
        assert target == legal_moves_1_3
        legal_moves_2_3 = universe.legal_moves_or_stop((2, 3))
        target = {north : (2, 2),
                  east  : (3, 3),
                  west  : (1, 3)}
        assert target == legal_moves_2_3
        # 3, 3 has the same options as 2, 3
        legal_moves_4_3 = universe.legal_moves_or_stop((4, 3))
        target = {west  : (3, 3)}
        assert target == legal_moves_4_3

    def test_move_bot_exceptions(self):
        test_move_bot = (
            """ ######
                #  #0#
                # 3 ##
                #2  1#
                ###### """)
        universe = CTFUniverse.create(test_move_bot, 4)

        with pytest.raises(IllegalMoveException):
            universe.move_bot(0, 'FOOBAR')
        with pytest.raises(IllegalMoveException):
            universe.move_bot(0, (0, 2))

        with pytest.raises(IllegalMoveException):
            universe.move_bot(0, north)
        with pytest.raises(IllegalMoveException):
            universe.move_bot(0, west)
        with pytest.raises(IllegalMoveException):
            universe.move_bot(0, south)
        with pytest.raises(IllegalMoveException):
            universe.move_bot(0, east)

        with pytest.raises(IllegalMoveException):
            universe.move_bot(1, north)
        with pytest.raises(IllegalMoveException):
            universe.move_bot(1, east)
        with pytest.raises(IllegalMoveException):
            universe.move_bot(1, south)

        with pytest.raises(IllegalMoveException):
            universe.move_bot(2, west)
        with pytest.raises(IllegalMoveException):
            universe.move_bot(2, south)

    def test_reset_bot_bot_positions(self):

        test_reset_bot = (
            """ ########
                #0     #
                #2    3#
                #     1#
                ######## """)
        number_bots = 4
        universe = CTFUniverse.create(test_reset_bot, number_bots)
        assert str(universe) == \
                str(Layout(test_reset_bot, layout_chars, number_bots).as_mesh())
        assert universe.bot_positions == \
                [(1, 1), (6, 3), (1, 2), (6, 2)]
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
        assert universe.bot_positions == \
                [(4, 1), (2, 2), (2, 3), (6, 1)]
        assert str(universe) == \
                str(Layout(test_shuffle, layout_chars, number_bots).as_mesh())
        universe.bots[0]._to_initial()
        universe.bots[1]._to_initial()
        universe.bots[2]._to_initial()
        universe.bots[3]._to_initial()
        assert str(universe) == \
                str(Layout(test_reset_bot, layout_chars, number_bots).as_mesh())
        assert universe.bot_positions == \
                [(1, 1), (6, 3), (1, 2), (6, 2)]

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
            universe = CTFUniverse.create(layout, number_bots)
            universe.teams[0].score = black_score
            universe.teams[1].score = white_score
            for i, pos in enumerate(initial_pos):
                universe.bots[i].initial_pos = pos
            if not (1, 2) in universe.food_list:
                universe.teams[1].score += 1
            if not (3, 1) in universe.food_list:
                universe.teams[0].score += 1
            return universe

        test_start = (
            """ ######
                #0 . #
                #.  1#
                ###### """)
        universe = CTFUniverse.create(test_start, number_bots)
        game_state = universe.move_bot(1, west)
        test_first_move = (
            """ ######
                #0 . #
                #. 1 #
                ###### """)
        assert create_TestUniverse(test_first_move) == universe
        assert game_state["bot_moved"][0] == {"bot_id": 1, "old_pos": (4, 2), "new_pos": (3, 2)}
        test_second_move = (
            """ ######
                #0 . #
                #.1  #
                ###### """)
        game_state = universe.move_bot(1, west)
        assert create_TestUniverse(test_second_move) == universe
        assert game_state["bot_moved"][0] == {"bot_id": 1, "old_pos": (3, 2), "new_pos": (2, 2)}
        test_eat_food = (
            """ ######
                #0 . #
                #1   #
                ###### """)
        unittest.TestCase().assertCountEqual(universe.food_list, [(3, 1), (1, 2)])
        game_state = universe.move_bot(1, west)
        assert create_TestUniverse(test_eat_food) == universe
        unittest.TestCase().assertCountEqual(universe.food_list, [(3, 1)])
        assert universe.teams[1].score == 1
        assert game_state == {
            "bot_moved": [{"bot_id": 1, "old_pos": (2, 2), "new_pos": (1, 2)}],
            "food_eaten": [{"bot_id": 1, "food_pos": (1,2)}],
            "bot_destroyed": []
            }

        test_destruction = (
            """ ######
                #  . #
                #0  1#
                ###### """)
        game_state = universe.move_bot(0, south)
        assert create_TestUniverse(test_destruction,
            black_score=universe.KILLPOINTS) == universe
        assert game_state == {
            "bot_moved": [{"bot_id": 0, "old_pos": (1, 1), "new_pos": (1, 2)}, {'old_pos': (1, 2), 'new_pos': (1, 2), 'bot_id': 0}],
            "food_eaten": [],
            "bot_destroyed": [{"bot_id": 1, "destroyed_by": 0}]
        }

        test_black_score = (
            """ ######
                #  0 #
                #   1#
                ###### """)
        universe.move_bot(0, north)
        universe.move_bot(0, east)
        game_state = universe.move_bot(0, east)
        assert create_TestUniverse(test_black_score,
            black_score=universe.KILLPOINTS) == universe
        unittest.TestCase().assertCountEqual(universe.food_list, [])
        assert universe.teams[0].score == universe.KILLPOINTS+1
        assert game_state == {
            "bot_moved": [{"bot_id": 0, "old_pos": (2, 1), "new_pos": (3, 1)}],
            "food_eaten": [{"bot_id": 0, "food_pos": (3, 1)}],
            "bot_destroyed": []
        }
        test_bot_suicide = (
            """ ######
                #0   #
                #   1#
                ###### """)
        universe.move_bot(0, east)
        game_state = universe.move_bot(0, south)
        assert create_TestUniverse(test_bot_suicide,
            black_score=universe.KILLPOINTS, white_score=universe.KILLPOINTS) == universe
        assert game_state == {
            "bot_moved": [{"bot_id": 0, "old_pos": (4, 1), "new_pos": (4, 2)}, {'old_pos': (4, 2), 'new_pos': (1, 1), 'bot_id': 0}],
            "food_eaten": [],
            "bot_destroyed": [{"bot_id": 0, "destroyed_by": 1}]
        }

    def test_no_eat_own_food(self):
        test_start = (
            """ ######
                #0 . #
                #.  1#
                ###### """)
        number_bots = 2
        universe = CTFUniverse.create(test_start, number_bots)
        universe.move_bot(1, north)
        game_state = universe.move_bot(1, west)
        unittest.TestCase().assertCountEqual(universe.food_list, [(3, 1), (1, 2)])
        assert game_state["bot_moved"][0] == {"bot_id": 1, "old_pos": (4, 1), "new_pos": (3, 1)}

    def test_suicide_win(self):
        test = (
            """ ######
                #0 .1#
                #.   #
                ###### """)
        universe = CTFUniverse.create(test, 2)
        universe.move_bot(0, east)
        universe.move_bot(1, west)
        game_state = universe.move_bot(0, east)
        target = {
            "bot_moved": [{"bot_id": 0, "old_pos": (2, 1), "new_pos": (3, 1)}, {"bot_id": 0, "old_pos": (3, 1), "new_pos": (1, 1)}],
            "food_eaten": [{"bot_id": 0, "food_pos": (3, 1)}],
            "bot_destroyed": [{"bot_id": 0, "destroyed_by": 1}]
        }
        assert game_state == target

    def test_double_kill(self):
        self.maxDiff = None
        test = (
            """ ######
                #02 1#
                #. .3#
                ###### """)
        universe = CTFUniverse.create(test, 4)
        universe.move_bot(0, east)
        universe.move_bot(1, west)
        game_state = universe.move_bot(1, west)
        target = {
            "bot_moved": [{"bot_id": 1, "old_pos": (3, 1), "new_pos": (2, 1)}, {"bot_id": 1, "old_pos": (2, 1), "new_pos": (4, 1)}],
            "food_eaten": [],
            "bot_destroyed": [{"bot_id": 1, "destroyed_by": 0}]
        }
        assert game_state == target
        assert universe.teams[0].score == universe.KILLPOINTS
        assert universe.teams[1].score == 0

