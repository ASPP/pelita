from pelita import gamestate_filters as gf
from pelita import layout as lt
import pytest
import random


def make_gamestate():

    # get layout
    layout = """
        ##################
        #. ... .##.     3#
        # # #  .  .### #1#
        # # ##.   .      #
        #      .   .## # #
        #0# ###.  .  # # #
        #2     .##. ... .#
        ################## """

    lt_dict = lt.parse_layout(layout)

    # prep input
    gamestate = {
        "turn": 1,
        "round": 3,
        "max_round": 300,
        "walls": lt_dict["walls"],
        "food": lt_dict["food"],
        "bots": lt_dict["bots"],
        "timeouts": [2, 3],
        "gameover": False,
        "whowins": None,
        "team_names": ["even", "odd"],
        "team_say": "pos!!",
        "score": [20, 10],
        "deaths": [2, 3],
        "noisy": [False] * 4,
    }

    return gamestate


def sub_test_noiser(new_bots, old_bots, turn, should_noise, test_other):
    """ sub test fuction to check if noiser worked

    Parameters
    ----------
    new_bots: bots after noising
    old_bots: bots before noising
    turn: which turn is it now? 0,1,2,3
    should_noise: hould the noiser do something right now, or return same bots?
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


def test_noiser_no_negative_coordinates():

    gamestate = make_gamestate()
    old_bots = gamestate["bots"]
    new_gamestate = gf.noiser(gamestate, noise_radius=5, sight_distance=5, seed=None)
    new_bots = new_gamestate["bots"]
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
        old_bots = gamestate["bots"]
        new_gamestate = gf.noiser(
            gamestate, noise_radius=5, sight_distance=5, seed=None
        )
        new_bots = new_gamestate["bots"]
        test_collect_bot0.append((not old_bots[0] == new_bots[0]))
        test_collect_bot2.append((not old_bots[2] == new_bots[2]))

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
        new_gamestate = gf.noiser(
            gamestate, noise_radius=5, sight_distance=5, seed=None
        )
        new_bots = new_gamestate["bots"]
        test_collect_bot0.append((not old_bots[0] == new_bots[0]))
        test_collect_bot2.append((not old_bots[2] == new_bots[2]))

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
        new_gamestate = gf.noiser(
            gamestate, noise_radius=5, sight_distance=5, seed=None
        )
        new_bots = new_gamestate["bots"]
        test_collect_bot1.append((not old_bots[1] == new_bots[1]))
        test_collect_bot3.append((not old_bots[3] == new_bots[3]))

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
        new_gamestate = gf.noiser(
            gamestate, noise_radius=5, sight_distance=5, seed=None
        )
        new_bots = new_gamestate["bots"]
        test_collect_bot1.append((not old_bots[1] == new_bots[1]))
        test_collect_bot3.append((not old_bots[3] == new_bots[3]))

    assert any(test_collect_bot1) or any(test_collect_bot3)


def test_noiser_not_noising_own_team_even0():

    """ It is the even team's turn, and the noiser should
    not work on own bots """

    gamestate = make_gamestate()
    gamestate["turn"] = 0
    old_bots = gamestate["bots"]
    new_gamestate = gf.noiser(gamestate, noise_radius=5, sight_distance=5, seed=None)
    new_bots = new_gamestate["bots"]
    test_bot0 = old_bots[0] == new_bots[0]
    test_bot2 = old_bots[2] == new_bots[2]

    assert test_bot0 or test_bot2


def test_noiser_not_noising_own_team_even2():

    """ It is the even team's turn, and the noiser should
    not work on own bots """

    gamestate = make_gamestate()
    gamestate["turn"] = 2
    old_bots = gamestate["bots"]
    new_gamestate = gf.noiser(gamestate, noise_radius=5, sight_distance=5, seed=None)
    new_bots = new_gamestate["bots"]
    test_bot0 = old_bots[0] == new_bots[0]
    test_bot2 = old_bots[2] == new_bots[2]

    assert test_bot0 or test_bot2


def test_noiser_not_noising_own_team_odd1():

    """ It is the odd team's turn, and the noiser should
    not work on own bots """

    gamestate = make_gamestate()
    gamestate["turn"] = 1
    old_bots = gamestate["bots"]
    new_gamestate = gf.noiser(gamestate, noise_radius=5, sight_distance=5, seed=None)
    new_bots = new_gamestate["bots"]
    test_bot1 = old_bots[1] == new_bots[1]
    test_bot3 = old_bots[3] == new_bots[3]

    assert test_bot1 or test_bot3


def test_noiser_not_noising_own_team_odd3():

    """ It is the odd team's turn, and the noiser should
    not work on own bots """

    gamestate = make_gamestate()
    gamestate["turn"] = 3
    old_bots = gamestate["bots"]
    new_gamestate = gf.noiser(gamestate, noise_radius=5, sight_distance=5, seed=None)
    new_bots = new_gamestate["bots"]
    test_bot1 = old_bots[1] == new_bots[1]
    test_bot3 = old_bots[3] == new_bots[3]

    assert test_bot1 or test_bot3


def test_noiser_not_noising_at_noise_radius0():

    """ It is the any team's turn, and the noiser should
    not do anything, because noise radius is 0 """

    test_collect = []
    for tt in range(4):
        gamestate = make_gamestate()
        gamestate["turn"] = tt
        old_bots = gamestate["bots"]
        new_gamestate = gf.noiser(
            gamestate, noise_radius=0, sight_distance=5, seed=None
        )
        new_bots = new_gamestate["bots"]
        sub_test_collect = []
        for ss in range(4):
            sub_test_collect.append((old_bots[1] == new_bots[1]))
        sub_test_collect.append(all(sub_test_collect))

    assert all(sub_test_collect)


@pytest.mark.parametrize("ii", range(30))
def test_noiser_noising_at_noise_radius_extreme(ii):

    """ It is the any team's turn, and the noiser should
    still noise within confines of maze, despite extreme radius """

    gamestate = make_gamestate()
    gamestate["turn"] = random.randint(0, 3)
    old_bots = gamestate["bots"]
    new_gamestate = gf.noiser(gamestate, noise_radius=50, sight_distance=5, seed=None)
    new_bots = new_gamestate["bots"]
    assert sub_test_noiser(new_bots, old_bots, gamestate["turn"], True, True)
