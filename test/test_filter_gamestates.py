
import pytest

import collections
import random

from pelita import gamestate_filters as gf
from pelita.game import setup_game, prepare_bot_state
from pelita.layout import parse_layout


def make_gamestate():
    def dummy_team(bot, state):
        return bot.position, state

    # get layout
    layout = """
        ##################
        #. ... .##.     y#
        # # #  .  .### #x#
        # # ##.   .      #
        #      .   .## # #
        #a# ###.  .  # # #
        #b     .##. ... .#
        ################## """

    lt_dict = parse_layout(layout)
    game_state = setup_game([dummy_team, dummy_team], layout_dict=lt_dict, max_rounds=1)

    return game_state


def sub_test_noiser(new_bots, old_bots, turn, should_noise, test_other):
    """ sub test function to check if noiser worked

    Parameters
    ----------
    new_bots: bots after noising
    old_bots: bots before noising
    turn: which turn is it now? 0,1,2,3
    should_noise: should the noiser do something right now, or return same bots?
    test_other: true: then it checks if what was meant to happen to other bots happened
                                    and vice versa

    Returns
    -------
    a boolean
    """

    if test_other:
        if not turn % 2:
            # even case
            if should_noise:
                test_bot1 = not old_bots[1] == new_bots[1]
                test_bot3 = not old_bots[3] == new_bots[3]
                return test_bot1 or test_bot3
            else:
                test_bot1 = old_bots[1] == new_bots[1]
                test_bot3 = old_bots[3] == new_bots[3]
                return test_bot1 and test_bot3
        else:
            if should_noise:
                test_bot0 = not old_bots[0] == new_bots[0]
                test_bot2 = not old_bots[2] == new_bots[2]
                return test_bot0 or test_bot2
            else:
                test_bot0 = old_bots[0] == new_bots[0]
                test_bot2 = old_bots[2] == new_bots[2]
                return test_bot0 and test_bot2
    else:
        # test_own should always mean no change
        if turn % 2:
            test_bot0 = old_bots[0] == new_bots[0]
            test_bot2 = old_bots[2] == new_bots[2]
            return test_bot0 and test_bot2
        else:
            test_bot1 = old_bots[1] == new_bots[1]
            test_bot3 = old_bots[3] == new_bots[3]
            return test_bot1 and test_bot3


@pytest.mark.parametrize("bot_id", range(4))
def test_noiser_no_negative_coordinates(bot_id):

    gamestate = make_gamestate()
    old_bots = gamestate["bots"][:]
    walls = gamestate['walls']
    shape = gamestate['shape']
    bot_position = gamestate['bots'][bot_id]
    enemy_group = 1 - (bot_id // 2)
    enemy_positions = gamestate['bots'][enemy_group::2]
    noised = gf.noiser(walls, shape=shape, bot_position=bot_position, enemy_positions=enemy_positions,
                       noise_radius=5, sight_distance=5, rnd=None)
    new_bots = noised["enemy_positions"]
    test_1 = all(item[0] > 0 for item in new_bots)
    test_2 = all(item[1] > 0 for item in new_bots)

    assert test_1 and test_2


def test_noiser_noising_odd_turn1():

    """ It is the odd team's turn, and the noiser should
    work on even bots """

    test_collect_bot0 = []
    test_collect_bot2 = []
    for ii in range(10):

        # we let it run 10 times because it could return the original position,
        # but in most cases it should return a different pos (due to noise)
        gamestate = make_gamestate()
        gamestate["turn"] = 1
        old_bots = gamestate["bots"]
        new_gamestate = prepare_bot_state(gamestate)
        new_bots = new_gamestate['enemy']['bot_positions']
        test_collect_bot0.append((not old_bots[0] == new_bots[0]))
        test_collect_bot2.append((not old_bots[2] == new_bots[1]))

    assert any(test_collect_bot0) or any(test_collect_bot2)


def test_noiser_noising_odd_turn3():

    """ It is the odd team's turn, and the noiser should
    work on even bots """

    test_collect_bot0 = []
    test_collect_bot2 = []
    for ii in range(10):

        # we let it run 10 times because it could return the original position,
        # but in most cases it should return a different pos (due to noise)
        gamestate = make_gamestate()
        gamestate["turn"] = 3
        old_bots = gamestate["bots"]
        new_gamestate = prepare_bot_state(gamestate)
        new_bots = new_gamestate['enemy']['bot_positions']
        test_collect_bot0.append((not old_bots[0] == new_bots[0]))
        test_collect_bot2.append((not old_bots[2] == new_bots[1]))

    assert any(test_collect_bot0) or any(test_collect_bot2)


def test_noiser_noising_even_turn0():

    """ It is the even team's turn, and the noiser should
    work on odd bots """

    test_collect_bot1 = []
    test_collect_bot3 = []
    for ii in range(10):

        # we let it run 10 times because it could return the original position,
        # but in most cases it should return a different pos (due to noise)
        gamestate = make_gamestate()
        gamestate["turn"] = 0
        old_bots = gamestate["bots"]
        new_gamestate = prepare_bot_state(gamestate)
        new_bots = new_gamestate['enemy']['bot_positions']
        test_collect_bot1.append((not old_bots[1] == new_bots[0]))
        test_collect_bot3.append((not old_bots[3] == new_bots[1]))

    assert any(test_collect_bot1) or any(test_collect_bot3)


def test_noiser_noising_even_turn2():

    """ It is the even team's turn, and the noiser should
    work on odd bots """

    test_collect_bot1 = []
    test_collect_bot3 = []
    for ii in range(10):

        # we let it run 10 times because it could return the original position,
        # but in most cases it should return a different pos (due to noise)
        gamestate = make_gamestate()
        gamestate["turn"] = 2
        old_bots = gamestate["bots"]
        new_gamestate = prepare_bot_state(gamestate)
        new_bots = new_gamestate['enemy']['bot_positions']
        test_collect_bot1.append((not old_bots[1] == new_bots[0]))
        test_collect_bot3.append((not old_bots[3] == new_bots[1]))

    assert any(test_collect_bot1) or any(test_collect_bot3)


def test_noiser_not_noising_own_team_even0():

    """ It is the even team's turn, and the noiser should
    not work on own bots """

    gamestate = make_gamestate()
    gamestate["turn"] = 0
    old_bots = gamestate["bots"]
    new_gamestate = prepare_bot_state(gamestate)
    new_bots = new_gamestate['team']['bot_positions']
    test_bot0 = old_bots[0] == new_bots[0]
    test_bot2 = old_bots[2] == new_bots[1]

    assert test_bot0 or test_bot2


def test_noiser_not_noising_own_team_even2():

    """ It is the even team's turn, and the noiser should
    not work on own bots """

    gamestate = make_gamestate()
    gamestate["turn"] = 2
    old_bots = gamestate["bots"]
    new_gamestate = prepare_bot_state(gamestate)
    new_bots = new_gamestate['team']['bot_positions']
    test_bot0 = old_bots[0] == new_bots[0]
    test_bot2 = old_bots[2] == new_bots[1]

    assert test_bot0 or test_bot2


def test_noiser_not_noising_own_team_odd1():

    """ It is the odd team's turn, and the noiser should
    not work on own bots """

    gamestate = make_gamestate()
    gamestate["turn"] = 1
    old_bots = gamestate["bots"]
    new_gamestate = prepare_bot_state(gamestate)
    new_bots = new_gamestate['team']['bot_positions']
    test_bot1 = old_bots[1] == new_bots[0]
    test_bot3 = old_bots[3] == new_bots[1]

    assert test_bot1 or test_bot3


def test_noiser_not_noising_own_team_odd3():

    """ It is the odd team's turn, and the noiser should
    not work on own bots """

    gamestate = make_gamestate()
    gamestate["turn"] = 3
    old_bots = gamestate["bots"]
    new_gamestate = prepare_bot_state(gamestate)
    new_bots = new_gamestate['team']['bot_positions']
    test_bot1 = old_bots[1] == new_bots[0]
    test_bot3 = old_bots[3] == new_bots[1]

    assert test_bot1 or test_bot3


def test_noiser_not_noising_at_noise_radius0():

    """ It is the any team's turn, and the noiser should
    not do anything, because noise radius is 0 """

    test_collect = []
    for tt in range(4):
        gamestate = make_gamestate()
        old_bots = gamestate["bots"]
        gamestate["turn"] = tt
        gamestate["noise_radius"] = 0
        new_gamestate = prepare_bot_state(gamestate)
        new_team_bots = new_gamestate['team']['bot_positions']
        new_enemy_bots = new_gamestate['enemy']['bot_positions']
        if tt % 2 == 0:
            # team 0
            assert old_bots[0] == new_team_bots[0]
            assert old_bots[1] == new_enemy_bots[0]
            assert old_bots[2] == new_team_bots[1]
            assert old_bots[3] == new_enemy_bots[1]
        else:
            # team 1
            assert old_bots[0] == new_enemy_bots[0]
            assert old_bots[1] == new_team_bots[0]
            assert old_bots[2] == new_enemy_bots[1]
            assert old_bots[3] == new_team_bots[1]


@pytest.mark.parametrize("ii", range(30))
def test_noiser_noising_at_noise_radius_extreme(ii):

    """ It is the any team's turn, and the noiser should
    still noise within confines of maze, despite extreme radius """

    gamestate = make_gamestate()
    gamestate["turn"] = random.randint(0, 3)
    team_id = gamestate["turn"] % 2
    old_bots = gamestate["bots"]
    team_bots = old_bots[team_id::2]
    enemy_bots = old_bots[1 - team_id::2]
    noised = gf.noiser(walls=gamestate["walls"],
                       shape=gamestate["shape"],
                       bot_position=gamestate["bots"][gamestate["turn"]],
                       enemy_positions=enemy_bots,
                       noise_radius=50, sight_distance=5, rnd=None)

    assert all(noised["is_noisy"])

    for noised_pos in noised["enemy_positions"]:
        # check that the noised position is legal
        assert noised_pos not in gamestate["walls"]
        assert 0 <= noised_pos[0] < max(gamestate["walls"])[0]
        assert 0 <= noised_pos[1] < max(gamestate["walls"])[1]


@pytest.mark.parametrize('noise_radius, expected', [
    [0, [(3, 3)]], # original position. not noised
    [1, [(2, 3), (3, 3), (4, 3)]],
    [2, [(1, 3), (2, 3), (3, 1), (3, 3), (4, 3), (5, 3)]],
    [5, [(1, 1), (1, 2), (1, 3), (2, 3), (3, 3),
         (4, 3), (5, 3), (6, 3), (7, 3), (7, 2),
         (6, 1), (5, 1), (4, 1), (3, 1)]]
])
def test_uniform_noise_manhattan(noise_radius, expected, test_layout=None):
    # Test how bot 1(x) observes bot 0(a)
    if not test_layout:
        test_layout = (
        """ ##################
            # #.  .  # .    y#
            # #####    ##### #
            #b a  . #  .  .#x#
            ################## """)
    parsed = parse_layout(test_layout)

    position_bucket = collections.defaultdict(int)
    for i in range(200):
        noised = gf.noiser(walls=parsed['walls'],
                            shape=parsed["shape"],
                            bot_position=parsed['bots'][1],
                            enemy_positions=[parsed['bots'][0]],
                            noise_radius=noise_radius)
        if noise_radius == 0:
            assert noised['is_noisy'] == [False]
        else:
            assert noised['is_noisy'] == [True]

        noised_pos = noised['enemy_positions'][0]
        position_bucket[noised_pos] += 1
    assert 200 == sum(position_bucket.values())
    # Since this is a randomized algorithm we need to be a bit lenient with
    # our tests. We check that each position was selected at least once.
    assert set(position_bucket.keys()) == set(expected)


@pytest.mark.parametrize('noise_radius, test_layout', [
    [0, """
        ##################
        # #      # y     #
        # #####    ##### #
        #b a    #      #x#
        ################## """], # original position. not noised
    [1, """
        ##################
        #   .       y    #
        #  .a.        x  #
        #b  .            #
        ################## """], # noised by one
    [1, """
        ##################
        # b          y   #
        #   .         x  #
        #  .a.           #
        ################## """], # noised by one
    [1, """
        ##################
        #  b          y  #
        #.            x  #
        #a.              #
        ################## """], # noised by one
    [1, """
        ##################
        #   b          .a#
        #  x        y   .#
        #                #
        ################## """], # noised by on
    [1, """
        ##################
        # #  b   #   y   #
        # #####    ##### #
        # .a.   #      #x#
        ################## """], # noised by one
    [1, """
        ##################
        # #   b  #    y  #
        # #####    #####.#
        #  x    #      #a#
        ################## """], # noised by one
    [1, """
        ##################
        # #   b  #   .a. #
        # #####    ##### #
        #  x    #    y # #
        ################## """], # noised by one
])
def test_uniform_noise_manhattan_graphical(noise_radius, test_layout):
    # Test how bot 1(x) observes bot 0(a)
    # the expected locations are where the food is placed
    parsed = parse_layout(test_layout)
    expected = parsed['food'] + [parsed['bots'][0]]
    test_uniform_noise_manhattan(noise_radius, expected, test_layout=test_layout)


@pytest.mark.parametrize('test_layout, is_noisy', [
    ["""
        ##################
        # #..  b #     # #
        #.#####y   ##### #
        #.#....  #     # #
        #.#####.   ##### #
        #..a..#..  #  x  #
        #.#####.   ##### #
        #.#....  #     # #
        #.#####    ##### #
        # #..    #     # #
        ################## """, True],
    ["""
        ##################
        # #    y #   ..# #
        # #####b   #####.#
        # #      # ....#.#
        # #####   .#####.#
        #  x  #  ..#..a..#
        # #####   .#####.#
        # #      # ....#.#
        # #####    #####.#
        # #      #   ..# #
        ################## """, True],
    ["""
        ##################
        # #..   y#     # #
        #.##### b  ##### #
        #.#....  #     # #
        #.#####.   ##### #
        #..a..#.. x#     #
        #.#####.   ##### #
        #.#....  #     # #
        #.#####    ##### #
        # #..    #     # #
        ################## """, True],
    ["""
        ##################
        # #..   y#     # #
        #.##### b  ##### #
        #.#....  #     # #
        #.#####.   ##### #
        #..a..#..x #     #
        #.#####.   ##### #
        #.#....  #     # #
        #.#####    ##### #
        # #..    #     # #
        ################## """, True],
        # when we move too close,
        # the noise disappears
    ["""
        ##################
        # #     y#     # #
        # ##### b  ##### #
        # #      #     # #
        # #####    ##### #
        #  a  # x  #     #
        # #####    ##### #
        # #      #     # #
        # #####    ##### #
        # #      #     # #
        ################## """, False],
])
def test_uniform_noise_manhattan_graphical_distance(test_layout, is_noisy):
    # Test how bot 1 observes bot 0
    # the expected locations are where the food is placed
    parsed = parse_layout(test_layout)
    expected = parsed['food'] + [parsed['bots'][0]]

    position_bucket = collections.defaultdict(int)
    NUM_TESTS = 400
    for i in range(NUM_TESTS):
        noised = gf.noiser(walls=parsed['walls'],
                            shape=parsed['shape'],
                            bot_position=parsed['bots'][1],
                            enemy_positions=[parsed['bots'][0]])
                            # use default values for radius and distance
                            # noise_radius=5, sight_distance=5
        assert noised['is_noisy'] == [is_noisy]

        noised_pos = noised['enemy_positions'][0]
        position_bucket[noised_pos] += 1
    assert NUM_TESTS == sum(position_bucket.values())
    # Since this is a randomized algorithm we need to be a bit lenient with
    # our tests. We check that each position was selected at least once.
    assert set(position_bucket.keys()) == set(expected)


def test_uniform_noise_4_bots_manhattan():
    test_layout = (
    """ ##################
        # #. b.  # .     #
        # #####    #####y#
        #   a  . # .  .#x#
        ################## """)
    parsed = parse_layout(test_layout)

    expected_0 = [(1, 1), (1, 2), (1, 3), (2, 3), (3, 3),
                  (4, 3), (5, 3), (6, 3), (7, 3), (7, 2),
                  (7, 1), (6, 1), (5, 1), (4, 1), (3, 1),
                  (8, 2), (8, 3)]
    position_bucket_0 = collections.defaultdict(int)

    expected_2 = [(1, 1), (1, 2), (2, 3), (3, 3), (4, 3),
                  (5, 3), (6, 3), (7, 3), (8, 2), (8, 1),
                  (7, 1), (6, 1), (5, 1), (4, 1), (3, 1),
                  (9, 2), (8, 3), (7, 2), (10, 1)]
    position_bucket_2 = collections.defaultdict(int)

    for i in range(200):
        noised = gf.noiser(walls=parsed['walls'],
                           shape=parsed['shape'],
                           bot_position=parsed['bots'][1],
                           enemy_positions=parsed['bots'][0::2])

        assert noised['is_noisy'] == [True, True]
        position_bucket_0[noised['enemy_positions'][0]] += 1
        position_bucket_2[noised['enemy_positions'][1]] += 1
    assert 200 == sum(position_bucket_0.values())
    assert 200 == sum(position_bucket_2.values())
    # Since this is a randomized algorithm we need to be a bit lenient with
    # our tests. We check that each position was selected at least once.
    assert set(position_bucket_0.keys()) == set(expected_0)
    assert set(position_bucket_2.keys()) == set(expected_2)


def test_uniform_noise_4_bots_no_noise_manhattan():
    test_layout = (
    """ ##################
        # #.  .  # . b   #
        # #####    #####y#
        #  a  . #  .  .#x#
        ################## """)
    parsed = parse_layout(test_layout)

    expected_0 = [(1, 1), (3, 1), (4, 1), (5, 1), (6, 1),
                  (1, 2), (1, 3), (2, 3), (3, 3), (4, 3), (5, 3),
                  (6, 3), (7, 3), (7, 2) ]
    position_bucket_0 = collections.defaultdict(int)

    expected_2 = [(13, 1)]
    position_bucket_2 = {(13, 1) : 0}

    for i in range(200):
        noised = gf.noiser(walls=parsed['walls'],
                           shape=parsed['shape'],
                           bot_position=parsed['bots'][1],
                           enemy_positions=parsed['bots'][0::2])

        assert noised['is_noisy'] == [True, False]
        position_bucket_0[noised['enemy_positions'][0]] += 1
        position_bucket_2[noised['enemy_positions'][1]] += 1
    assert 200 == sum(position_bucket_0.values())
    assert 200 == sum(position_bucket_2.values())
    # Since this is a randomized algorithm we need to be a bit lenient with
    # our tests. We check that each position was selected at least once.
    assert set(position_bucket_0.keys()) == set(expected_0)
    assert set(position_bucket_2.keys()) == set(expected_2)


def test_noise_manhattan_failure():
    test_layout = (
    """ ##################
        ########## . b   #
        ########## #####y#
        ###a###### .  . x#
        ################## """)
    # we test what bot 1 sees
    # bot 0 should not be noised
    # bot 2 should not be noised
    parsed = parse_layout(test_layout)
    expected = parsed['food'] + [parsed['bots'][0]]

    position_bucket = collections.defaultdict(int)
    # check a few times
    for i in range(5):
        noised = gf.noiser(walls=parsed['walls'],
                            shape=parsed['shape'],
                            bot_position=parsed['bots'][1],
                            enemy_positions=parsed['bots'][0::2])

        assert noised['is_noisy'] == [False, False]
        noised_pos = noised['enemy_positions']
        assert noised_pos == parsed['bots'][0::2]
