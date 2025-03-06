"""Tests for Pelita game module"""
import inspect
import itertools
import os
import sys
from contextlib import contextmanager
from pathlib import Path
from random import Random

from pelita.network import RemotePlayerRecvTimeout
import pytest

from pelita import game, layout, maze_generator
from pelita.exceptions import NoFoodWarning, PelitaBotError
from pelita.game import (add_fatal_error, apply_move, get_legal_positions, initial_positions,
                         play_turn, run_game, setup_game)
from pelita.layout import parse_layout
from pelita.player import stepping_player, stopping_player

_mswindows = (sys.platform == "win32")

FIXTURE_DIR = Path(__file__).parent.resolve() / 'fixtures'


@contextmanager
def temp_wd(path):
    """ Temporarily change the working directory to path. """
    old = os.getcwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(old)

small_layout = """
##################
#. ... .##.     y#
# # #  .  .### #x#
# # ##.   .      #
#      .   .## # #
#a# ###.  .  # # #
#b     .##. ... .#
##################
"""

@pytest.fixture
def game_state(round=1, turn=0, layout=small_layout):
    """helper fixture for a game_state"""
    parsed_l = parse_layout(layout)

    game_state = setup_game([stopping_player, stopping_player], layout_dict=parsed_l)
    game_state['round'] = round
    game_state['turn'] = turn
    return game_state


# dummy bot for setup_game tests
def dummy_bot(_bot, _state):
    raise NotImplementedError("This bot does not support moving")


def test_too_few_registered_teams():
    test_layout_4 = (
    """ ##################
        #a#.  .  # .     #
        #b#####    #####x#
        #     . #  .  .#y#
        ################## """)
    team_1 = dummy_bot
    with pytest.raises(ValueError):
        setup_game([team_1], layout_dict=parse_layout(test_layout_4), max_rounds=300)


def test_too_many_registered_teams():
    test_layout_4 = (
    """ ##################
        #a#.  .  # .     #
        #b#####    #####x#
        #     . #  .  .#y#
        ################## """)
    team_1 = dummy_bot
    with pytest.raises(ValueError):
        setup_game([team_1] * 3, layout_dict=parse_layout(test_layout_4), max_rounds=300)


@pytest.mark.parametrize('layout_str', [
    """
    ######
    #a y #
    # b x#
    ######
    """,
    """
    ######
    #a y.#
    # b x#
    ######
    """])
def test_no_food(layout_str):
    with pytest.warns(NoFoodWarning):
        parsed = parse_layout(layout_str)
        setup_game([dummy_bot, dummy_bot], layout_dict=parsed, max_rounds=300)


def test_initial_positions_basic():
    """Checks basic example for initial positions"""
    simple_layout = """
    ########
    #a ##b #
    #x   y #
    ########
    """
    parsed = parse_layout(simple_layout)
    out = initial_positions(parsed['walls'], parsed['shape'])
    exp = [(1, 1), (6, 2), (1, 2), (6, 1)]
    assert len(out) == 4
    assert out == exp


@pytest.mark.parametrize('simple_layout', [
    # We use these test layouts to check that our algorithm finds
    # the expected initial position. This is noted by the location
    # of the respective bots in the layout.
    """
    ########
    #a### y#
    #b    x#
    ########
    """,
    """
    ########
    ##### y#
    #ba   x#
    ########
    """,
    """
    ########
    #a###xy#
    #b    ##
    ########
    """,
    """
    ########
    #####x##
    ##ba  y#
    ########
    """,
    ])
def test_initial_positions(simple_layout):
    parsed = parse_layout(simple_layout)
    i_pos = initial_positions(parsed['walls'], parsed['shape'])
    expected = parsed['bots']
    assert len(i_pos) == 4
    assert i_pos == expected


@pytest.mark.parametrize('parsed_l', [maze_generator.generate_maze() for _ in range(30)])
def test_initial_positions_same_in_layout_random(parsed_l):
    """Check initial positions are the same as what the layout says for 30 random layouts"""
    exp = parsed_l["bots"]
    walls = parsed_l["walls"]
    shape = parsed_l["shape"]
    out = initial_positions(walls, shape)
    assert out == exp


def test_get_legal_positions_basic():
    """Check that the output of legal moves contains all legal moves for one example layout"""
    parsed_l = parse_layout(small_layout)
    legal_positions = get_legal_positions(parsed_l["walls"], parsed_l["shape"], parsed_l["bots"][0])
    exp = [(1, 4), (1, 6), (1, 5)]
    assert legal_positions == exp

@pytest.mark.parametrize('parsed_l', [maze_generator.generate_maze() for _ in range(50)])
@pytest.mark.parametrize('bot_idx', (0, 1, 2, 3))
def test_get_legal_positions_random(parsed_l, bot_idx):
    """Check that the output of legal moves returns only moves that are 1 field away and not inside a wall"""
    bot = parsed_l["bots"][bot_idx]
    legal_positions = get_legal_positions(parsed_l["walls"], parsed_l["shape"], bot)
    for move in legal_positions:
        assert move not in parsed_l["walls"]
        assert  abs((move[0] - bot[0])+(move[1] - bot[1])) <= 1

@pytest.mark.parametrize('turn', (0, 1, 2, 3))
def test_illegal_position_is_fatal(game_state, turn):
    """check that quits when illegal position"""
    game_state["turn"] = turn
    team = turn % 2
    # we pretend that two rounds have already been played
    game_state["round"] = 3

    illegal_position = (0, 0) # should always be a wall
    game_state_new = apply_move(game_state, illegal_position)
    assert game_state_new["gameover"]
    assert len(game_state_new["fatal_errors"][team]) == 1
    assert game_state_new["whowins"] == int(not team)
    assert game_state_new["fatal_errors"][team][0]['type'] == 'IllegalPosition'
    assert '(0, 0)' in game_state_new["fatal_errors"][team][0]['description']


@pytest.mark.parametrize('turn', (0, 1, 2, 3))
def test_play_turn_fatal(game_state, turn):
    """Checks that game quite after fatal error"""
    game_state["turn"] = turn
    game_state["round"] = 1
    game_state["game_phase"] = "RUNNING"
    team = turn % 2
    add_fatal_error(game_state, round=1, turn=turn, type="some error", msg="")
    # move = get_legal_positions(game_state["walls"], game_state["shape"], game_state["bots"][turn])
    # game_state_new = apply_move(game_state, move[0])
    assert game_state["game_phase"] == "FINISHED"
    assert game_state["gameover"]
    assert game_state["whowins"] == int(not team)


@pytest.mark.parametrize('turn', (0, 1, 2, 3))
@pytest.mark.parametrize('which_food', (0, 1))
def test_play_turn_eating_enemy_food(game_state, turn, which_food):
    """Check that you eat enemy food but not your own"""
    ### 012345678901234567
    #0# ##################
    #1# #. ... .##.     y#
    #2# # # #  .  .### #x#
    #3# # # ##.   .      #
    #4# #      .   .## # #
    #5# #a# ###.  .  # # #
    #6# #2     .##. ... .#
    #7# ##################
    team = turn % 2
    game_state['turn'] = turn
    prev_len_food = [len(team_food) for team_food in game_state["food"]]

    if which_food == 0:
        # Try to eat food on left side
        game_state["bots"][turn] = (6, 4)
        move = (7, 4)
    else:
        # Try to eat food on right side
        game_state["bots"][turn] = (11, 1)
        move = (10, 1)

    game_state_new = apply_move(game_state, move)

    if team == which_food:
        # No changes for either team
        assert game_state_new["score"][team] == 0
        assert game_state_new["score"][1 - team] == 0
        assert prev_len_food[team] == len(game_state_new["food"][team])
        assert prev_len_food[1 - team] == len(game_state_new["food"][1 - team])
    elif team != which_food:
        # Own team gains points, other team loses food
        assert game_state_new["score"][team] > 0
        assert game_state_new["score"][1 - team] == 0
        assert prev_len_food[team] == len(game_state_new["food"][team])
        assert prev_len_food[1 - team] > len(game_state_new["food"][1 - team])


@pytest.mark.parametrize('turn', (0, 1, 2, 3))
def test_play_turn_killing(game_state, turn):
    """Check that you can kill enemies but not yourself"""
    ### 012345678901234567
    #0# ##################
    #1# #. ... .##.     y#
    #2# # # #  .  .### #x#
    #3# # # ##.   .      #
    #4# #      .   .## # #
    #5# #a# ###.  .  # # #
    #6# #b     .##. ... .#
    #7# ##################
    team = turn % 2
    game_state["turn"] = turn
    enemy_idx = (1, 3) if team == 0 else(0, 2)
    (friend_idx,) = set([0, 1, 2, 3]) - set([*enemy_idx, turn])

    game_state_new = apply_move(game_state, game_state["bots"][friend_idx])
    # assert game_state_new["DEATHS"][team] == 5
    assert game_state_new["score"] == [0, 0]
    assert game_state_new["deaths"] == [0]*4

@pytest.mark.parametrize('setups', ((0, (1, 4)),
                                    (1, (16, 3)),
                                    (2, (2, 6)),
                                    (3, (15, 1))))
def test_play_turn_friendly_fire(game_state, setups):
    """Check that you can kill enemies but not yourself"""
    ### 012345678901234567
    #0# ##################
    #1# #. ... .##.     y#
    #2# # # #  .  .### #x#
    #3# # # ##.   .      #
    #4# #      .   .## # #
    #5# #a# ###.  .  # # #
    #6# #b     .##. ... .#
    #7# ##################
    turn = setups[0]
    enemy_pos = setups[1]
    team = turn % 2
    game_state["turn"] = turn
    enemy_idx = (1, 3) if team == 0 else (0, 2)
    game_state["bots"][enemy_idx[0]] = enemy_pos
    game_state_new = apply_move(game_state, enemy_pos)
    # assert game_state_new["DEATHS"][team] == 5
    assert game_state_new["score"][team] == 5


def test_multiple_enemies_killing():
    """ Check that you can kill multiple enemies at once. """

    l0 = """
    ########
    #  ..  #
    # bxa  #
    ########
    """

    l1 = """
    ########
    #  ..  #
    #  xay #
    ########
    """

    parsed_l0 = parse_layout(l0, bots={'y':(3,2)})
    for bot in (0, 2):
        game_state = setup_game([dummy_bot, dummy_bot], layout_dict=parsed_l0)

        game_state['round'] = 1
        game_state['turn'] = bot
        # get position of bots x (and y)
        kill_position = game_state['bots'][1]
        assert kill_position == game_state['bots'][3]
        new_state = apply_move(game_state, kill_position)
        # team 0 scores twice
        assert new_state['score'] == [10, 0]
        # bots 1 and 3 are back to origin
        assert new_state['bots'][1::2] == [(6, 2), (6, 1)]

    parsed_l1 = parse_layout(l1, bots={'b':(4,2)})
    for bot in (1, 3):
        game_state = setup_game([dummy_bot, dummy_bot], layout_dict=parsed_l1)

        game_state['round'] = 1
        game_state['turn'] = bot
        # get position of bots 0 (and 2)
        kill_position = game_state['bots'][0]
        assert kill_position == game_state['bots'][2]
        new_state = apply_move(game_state, kill_position)
        # team 1 scores twice
        assert new_state['score'] == [0, 10]
        # bots 0 and 2 are back to origin
        assert new_state['bots'][0::2] == [(1, 1), (1, 2)]


def test_suicide():
    """ Check that suicide works. """

    l0 = """
    ########
    #  ..  #
    #ybxa  #
    ########
    """

    l1 = """
    ########
    #  ..  #
    #  xayb#
    ########
    """

    parsed_l0 = parse_layout(l0)
    for bot in (1, 3):
        game_state = setup_game([dummy_bot, dummy_bot], layout_dict=parsed_l0)

        game_state['round'] = 1
        game_state['turn'] = bot
        # get position of bot 2
        suicide_position = game_state['bots'][2]
        new_state = apply_move(game_state, suicide_position)
        # team 0 scores
        assert new_state['score'] == [5, 0]
#        # bots 1 and 3 are back to origin
        if bot == 1:
            assert new_state['bots'][1::2] == [(6, 2), (1, 2)]
        elif bot == 3:
            assert new_state['bots'][1::2] == [(3, 2), (6, 1)]

    parsed_l1 = parse_layout(l1)
    for bot in (0, 2):
        game_state = setup_game([dummy_bot, dummy_bot], layout_dict=parsed_l1)

        game_state['round'] = 1
        game_state['turn'] = bot
        # get position of bot 3
        suicide_position = game_state['bots'][3]
        new_state = apply_move(game_state, suicide_position)
        # team 0 scores
        assert new_state['score'] == [0, 5]


def test_cascade_kill_red():
    cascade = [
    ("""
    ########
    #x ..ya#
    #     b#
    ########
    """, {}),

    # intermediate (hidden) stages

    # ########
    # #a .. y#
    # #     b#
    # ########
    # {'x':(1,1)}),

    # ########
    # #a .. y#
    # #     x#
    # ########
    # {'b':(6,2)}),

    ("""
    ########
    #a .. y#
    #b    x#
    ########
    """, {}),
    ]

    def move(bot, state):
        if not bot.is_blue and bot.turn == 1 and bot.round == 1:
            return (6, 1)
        return bot.position
    layouts = [parse_layout(l, bots=b) for l,b in cascade]
    state = setup_game([move, move], max_rounds=5, layout_dict=layouts[0])
    assert state['bots'] == layouts[0]['bots']
    state = game.play_turn(state) # Bot 0 stands
    assert state['bots'] == layouts[0]['bots']
    state = game.play_turn(state) # Bot 1 stands
    assert state['bots'] == layouts[0]['bots']
    state = game.play_turn(state) # Bot 2 stands
    assert state['bots'] == layouts[0]['bots']
    # Bot y moves, kills a. Bot a lands on and kills Bot x. Bot x lands on and kills Bot b. Bot b respawns
    state = game.play_turn(state)

    assert state['bots'] == layouts[1]['bots']
    assert state["score"] == [game.KILL_POINTS,game.KILL_POINTS*2]
    assert state["deaths"] == [1,1,1,0]
    assert state["kills"] == [1,1,0,1]
    assert state["bot_was_killed"] == [True, True, True, False]


def test_cascade_kill_blue():
    # this is the same as cascade kill, we just test the other team
    cascade = [
    ("""
    ########
    #ya.. b#
    #x     #
    ########
    """,{}),

    # intermediate (hidden) stages

    # ########
    # #a .. y#
    # #x     #
    # ########
    # {'b':(6,1)}),

    # ########
    # #a .. y#
    # #b     #
    # ########
    # {'x':(1,2)}),

    ("""
    ########
    #a .. y#
    #b    x#
    ########
    """, {}),
    ]
    def move(bot, state):
        if bot.is_blue and bot.turn == 0 and bot.round == 1:
            return (1, 1)
        return bot.position
    layouts = [parse_layout(l, bots=b) for l,b in cascade]
    state = setup_game([move, move], max_rounds=5, layout_dict=layouts[0])
    assert state['bots'] == layouts[0]['bots']
    # Bot a moves, kills Bot y. Bot y lands on and kills Bot b. Bot b lands on and kills Bot x.
    state = game.play_turn(state)

    assert state['bots'] == layouts[1]['bots']
    assert state["score"] == [game.KILL_POINTS*2, game.KILL_POINTS]
    assert state["deaths"] == [0,1,1,1]
    assert state["kills"] == [1,0,1,1]
    assert state["bot_was_killed"] == [False, True, True, True]


def test_cascade_suicide():
    cascade = [
    ("""
    ########
    #x ..ay#
    #     b#
    ########
    """,{}),

    ("""
    ########
    #a .. y#
    #b    x#
    ########
    """,{}),
    ]
    def move(bot, state):
        if bot.is_blue and bot.turn == 0 and bot.round == 1:
            return (6, 1)
        return bot.position
    layouts = [parse_layout(l, bots=b) for l,b in cascade]
    state = setup_game([move, move], max_rounds=5, layout_dict=layouts[0])
    assert state['bots'] == layouts[0]['bots']
    state = game.play_turn(state) # Bot 0 moves onto 3. Gets killed. Bot 0 and 1 are on same spot.
    assert state['bots'] == layouts[1]['bots']

    assert state["score"] == [game.KILL_POINTS, game.KILL_POINTS * 2]
    assert state["kills"] == [1, 1, 0, 1]
    assert state["deaths"] == [1, 1, 1, 0]
    assert state["bot_was_killed"] == [True, True, True, False]

def test_double_cascade_a():
    # test that a dual kill will also cascade properly
    cascade = [
    ("""
    ########
    #xa.. b#
    #      #
    ########
    """,{'y': (1, 1)}),

    ("""
    ########
    #a .. y#
    #b    x#
    ########
    """, {}),
    ]
    def move(bot, state):
        if bot.is_blue and bot.turn == 0 and bot.round == 1:
            return (1, 1)
        return bot.position
    layouts = [parse_layout(l, bots=b) for l,b in cascade]
    state = setup_game([move, move], max_rounds=5, layout_dict=layouts[0])
    assert state['bots'] == layouts[0]['bots']

    # x and y are on the same spot
    assert state['bots'][1] == state['bots'][3]

    # Bot a moves, kills bots x, y. Bot y lands on and kills Bot b, bot x respawns, bot b respawns
    state = game.play_turn(state)

    assert state['bots'] == layouts[1]['bots']
    assert state["score"] == [game.KILL_POINTS * 2, game.KILL_POINTS]
    assert state["deaths"] == [0,1,1,1]
    assert state["kills"] == [2,0,0,1]
    assert state["bot_was_killed"] == [False, True, True, True]

def test_double_cascade_b():
    # test that a dual kill will also cascade properly
    cascade = [
    ("""
    ########
    #xa..  #
    #     b#
    ########
    """,{'y': (1, 1)}),

    ("""
    ########
    #a .. y#
    #b    x#
    ########
    """, {}),
    ]
    def move(bot, state):
        if bot.is_blue and bot.turn == 0 and bot.round == 1:
            return (1, 1)
        return bot.position
    layouts = [parse_layout(l, bots=b) for l,b in cascade]
    state = setup_game([move, move], max_rounds=5, layout_dict=layouts[0])
    assert state['bots'] == layouts[0]['bots']

    # x and y are on the same spot
    assert state['bots'][1] == state['bots'][3]

    # Bot a moves, kills bots x, y. Bot x lands on and kills Bot b, bot y respawns, bot b respawns
    state = game.play_turn(state)

    assert state['bots'] == layouts[1]['bots']
    assert state["score"] == [game.KILL_POINTS * 2, game.KILL_POINTS]
    assert state["deaths"] == [0,1,1,1]
    assert state["kills"] == [2,1,0,0]
    assert state["bot_was_killed"] == [False, True, True, True]

def test_moving_through_maze():
    test_start = """
        ######
        #a . #
        #.. x#
        #b  y#
        ###### """
    parsed = parse_layout(test_start)
    teams = [
        stepping_player('>-v>>>-', '-^^->->'),
        stepping_player('<<-<<<-', '-------')
    ]
    state = setup_game(teams, layout_dict=parsed, max_rounds=8)

    # play first round
    for i in range(4):
        state = game.play_turn(state)
    test_first_round = parse_layout(
        """ ######
            # a. #
            #..x #
            #b  y#
            ###### """)

    assert test_first_round['bots'] == state['bots']
    assert test_first_round['food'] == list(state['food'][0]) + list(state['food'][1])
    assert state['score'] == [0, 0]

    for i in range(4):
        state = game.play_turn(state)
    test_second_round = parse_layout(
        """ ######
            # a. #
            #bx  #
            #   y#
            ###### """, bots={'b': (1, 2)}, food=[(1, 2)]) # b sitting on food

    assert test_second_round['bots'] == state['bots']
    assert test_second_round['food'] == list(state['food'][0]) + list(state['food'][1])
    assert state['score'] == [0, 1]

    for i in range(4):
        state = game.play_turn(state)
    test_third_round = parse_layout(
        """ ######
            #b . #
            #.a x#
            #   y#
            ###### """)

    assert test_third_round['bots'] == state['bots']
    assert test_third_round['food'] == list(state['food'][0]) + list(state['food'][1])
    assert state['score'] == [game.KILL_POINTS, 1]

    for i in range(4):
        state = game.play_turn(state)
    test_fourth_round = parse_layout(
        """ ######
            #b . #
            #a x #
            #   y#
            ###### """, bots={'a': (1, 2)}, food=[(1, 2)]) # a sitting on food

    assert test_fourth_round['bots'] == state['bots']
    assert test_fourth_round['food'] == list(state['food'][0]) + list(state['food'][1])
    assert state['score'] == [game.KILL_POINTS, game.KILL_POINTS + 1]

    for i in range(4):
        state = game.play_turn(state)
    test_fifth_round = parse_layout(
        """ ######
            # b. #
            #.a x#
            #   y#
            ###### """)
    assert test_fifth_round['bots'] == state['bots']
    assert test_fifth_round['food'] == list(state['food'][0]) + list(state['food'][1])
    assert state['score'] == [game.KILL_POINTS * 2, game.KILL_POINTS + 1]

    for i in range(4):
        state = game.play_turn(state)
    test_sixth_round = parse_layout(
        """
            ######
            # b. #
            #a x #
            #   y#
            ###### """, bots={'a': (1, 2)}, food=[(1, 2)]) # a sitting on food

    assert test_sixth_round['bots'] == state['bots']
    assert test_sixth_round['food'] == list(state['food'][0]) + list(state['food'][1])
    assert state['score'] == [game.KILL_POINTS * 2, game.KILL_POINTS * 2+ 1]

    for i in range(3): # !! Only move three bots
        state = game.play_turn(state)

    test_seventh_round = parse_layout(
        """
            ######
            #  b #
            #a x #
            #   y#
            ###### """, bots={'a': (1, 2)}, food=[(1, 2)]) # a sitting on food

    assert test_seventh_round['bots'] == state['bots']
    assert test_seventh_round['food'] == list(state['food'][0]) + list(state['food'][1])
    assert state['score'] == [game.KILL_POINTS * 2 + 1, game.KILL_POINTS * 2 + 1]
    assert state['gameover'] is True
    assert state['whowins'] == 2

    with pytest.raises(ValueError):
        state = game.play_turn(state)


@pytest.mark.parametrize('score', ([[3, 3], 2], [[1, 13], 1], [[13, 1], 0]))
def test_play_turn_maxrounds(game_state, score):
    """Check that game quits at maxrounds and choses correct winner"""
    # this works for ties as well, because there are no points to be gained at init positions
    game_state["round"] = 301
    game_state["score"] = score[0]
    game_state_new = game.play_turn(game_state)
    assert game_state_new["gameover"]
    assert game_state_new["whowins"] == score[1]

def test_play_turn_move():
    """Checks that bot is moved to intended space"""
    turn = 0
    parsed_l = parse_layout(small_layout)
    game_state = {
        "food": parsed_l["food"],
        "walls": parsed_l["walls"],
        "bots": parsed_l["bots"],
        "shape": parsed_l["shape"],
        "max_rounds": 300,
        "team_names": ("a", "b"),
        "turn": turn,
        "round": 0,
        "timeout": [],
        "gameover": False,
        "whowins": None,
        "team_say": "bla",
        "score": 0,
        "error_limit": 5,
        "kills":[0]*4,
        "deaths": [0]*4,
        "bot_was_killed": [False]*4,
        "timeouts": [[], []],
        "fatal_errors": [{}, {}],
        "rng": Random(),
        "game_phase": "RUNNING",
        }
    legal_positions = get_legal_positions(game_state["walls"], game_state["shape"], game_state["bots"][turn])
    game_state_new = apply_move(game_state, legal_positions[0])
    assert game_state_new["bots"][turn] == legal_positions[0]


def test_max_rounds():
    l = """
    ########
    #ba..xy#
    #      #
    ########
    """
    def move(bot, s):
        # in the first round (round #1),
        # all bots move to the south
        if bot.round == 1:
            return (bot.position[0], bot.position[1] + 1)
        else:
            # There should not be more then one round in this test
            raise RuntimeError("We should not be here in this test")

    l = parse_layout(l)
    assert l['bots'][0] == (2, 1)
    assert l['bots'][1] == (5, 1)
    assert l['bots'][2] == (1, 1)
    assert l['bots'][3] == (6, 1)
    # max_rounds == 1 should call move just once
    final_state = run_game([move, move], layout_dict=l, max_rounds=1)
    assert final_state['round'] == 1
    assert final_state['bots'][0] == (2, 2)
    assert final_state['bots'][1] == (5, 2)
    assert final_state['bots'][2] == (1, 2)
    assert final_state['bots'][3] == (6, 2)
    # max_rounds == 2 should finish and have the first team lose
    final_state = run_game([move, move], layout_dict=l, max_rounds=2)
    assert final_state['round'] == 2
    assert final_state['turn'] == 0
    assert final_state['bots'][0] == (2, 2)
    assert final_state['bots'][1] == (5, 2)
    assert final_state['bots'][2] == (1, 2)
    assert final_state['bots'][3] == (6, 2)
    assert final_state['gameover']
    assert final_state['whowins'] == 1
    assert final_state['fatal_errors'][0][0] == {
        'type': 'RuntimeError',
        'description': 'We should not be here in this test',
        'round': 2,
        'turn': 0,
    }


def test_update_round_counter():
    tests = {
        (None, None): (1, 0),
        (1, 0): (1, 1),
        (1, 1): (1, 2),
        (1, 2): (1, 3),
        (1, 3): (2, 0),
        (2, 3): (3, 0)
    }

    for (round0, turn0), (round1, turn1) in tests.items():
        res = game.next_round_turn({'turn': turn0,
                                    'round': round0,
                                    'gameover': False,})
        assert all(item in res.items() for item in {'turn': turn1, 'round': round1}.items())

    for (round0, turn0), (round1, turn1) in tests.items():
        with pytest.raises(ValueError):
            res = game.next_round_turn({'turn': turn0,
                                        'round': round0,
                                        'gameover': True,})

@pytest.mark.parametrize(
    'max_rounds, current_round, turn, game_phase, gameover', [
        [1, None, None, 'INIT', False],
        [1, 1, 0, 'RUNNING', False],
        [1, 1, 3, 'RUNNING', True],
    ])
def test_last_round_check(max_rounds, current_round, turn, game_phase, gameover):
    state = {
        'max_rounds': max_rounds,
        'round': current_round,
        'turn': turn,
        'error_limit': 5,
        'fatal_errors': [[],[]],
        'timeouts': [[],[]],
        'gameover': False,
        'score': [0, 0],
        'food': [{(1,1)}, {(1,1)}], # dummy food
        'game_phase': game_phase
    }
    res = game.check_gameover(state)
    assert res['gameover'] == gameover


@pytest.mark.parametrize(
    'team_errors, team_wins', [
        (((0, 0), (0, 0)), False),
        (((0, 1), (0, 0)), False),
        (((0, 0), (0, 1)), False),
        (((0, 2), (0, 2)), False),
        (((0, 4), (0, 0)), False),
        (((0, 0), (0, 4)), False),
        (((0, 4), (0, 4)), False),
        (((0, 5), (0, 0)), 1),
        (((0, 0), (0, 5)), 0),
        (((0, 5), (0, 5)), 1), # earlier team fails first
        (((1, 0), (0, 0)), 1),
        (((0, 0), (1, 0)), 0),
        (((1, 0), (1, 0)), 1), # earlier team fails first
        (((1, 1), (1, 0)), 1), # earlier team fails first
        (((1, 0), (0, 5)), 1),
        (((0, 5), (1, 0)), 0),
    ]
)
def test_error_finishes_game(team_errors, team_wins):
    # the mapping is as follows:
    # [(num_fatal_0, num_errors_0), (num_fatal_1, num_errors_1), result_flag]
    # the result flag: 0/1: team 0/1 wins, 2: draw, False: draw after 20 rounds

    (fatal_0, timeouts_0), (fatal_1, timeouts_1) = team_errors

    def move0(b, s):
        if not s:
            s['count'] = 0
        s['count'] += 1

        if s['count'] <= fatal_0:
            return None

        if s['count'] <= timeouts_0:
            raise RemotePlayerRecvTimeout

        return b.position

    def move1(b, s):
        if not s:
            s['count'] = 0
        s['count'] += 1

        if s['count'] <= fatal_1:
            return None

        if s['count'] <= timeouts_1:
            raise RemotePlayerRecvTimeout

        return b.position

    l = maze_generator.generate_maze()
    state = game.setup_game([move0, move1], max_rounds=20, layout_dict=l)

    # We must patch apply_move_fn so that RemotePlayerRecvTimeout is not caught
    # and we can actually test timeouts
    def apply_move_fn(move_fn, bot, state):
        move = move_fn(bot, state)
        if move is None:
            return {
                'error': 'Some fatal error',
                'error_msg': 'Some fatal error'
            }
        return { "move": move }

    state['teams'][0].apply_move_fn = apply_move_fn
    state['teams'][1].apply_move_fn = apply_move_fn

    # Play the game until it is gameover.
    while state['game_phase'] == 'RUNNING':
        # play the next turn
        state = play_turn(state)

    res = game.check_gameover(state)
    if team_wins is False:
        assert res["whowins"] == 2
        assert res["gameover"] is True
        assert state["round"] == 20
        assert len(state['timeouts'][0]) == timeouts_0
        assert len(state['timeouts'][1]) == timeouts_1
    else:
        assert res["whowins"] == team_wins
        assert res["gameover"] is True
        assert state["round"] < 20


@pytest.mark.parametrize('bot_to_move', [0, 1, 2, 3])
def test_finished_when_no_food(bot_to_move):
    """ Test that the game is over when a team has eaten its food. """
    l = """
    ########
    #  a.b #
    # y.x  #
    ########
    """
    bot_turn = bot_to_move // 2
    team_to_move = bot_to_move % 2
    def move(bot, s):
        if team_to_move == 0 and bot.is_blue and bot_turn == bot._bot_turn:
            return (4, 1)
            # eat the food between 0 and 2
        if team_to_move == 1 and (not bot.is_blue) and bot_turn == bot._bot_turn:
            # eat the food between 3 and 1
            return (3, 2)
        return bot.position

    l = parse_layout(l)
    final_state = run_game([move, move], layout_dict=l, max_rounds=20)
    assert final_state['round'] == 1
    assert final_state['turn'] == bot_to_move


def test_minimal_game():
    def move(b, s):
        return b.position

    l = maze_generator.generate_maze()
    final_state = run_game([move, move], max_rounds=20, layout_dict=l)
    assert final_state['gameover'] is True
    assert final_state['score'] == [0, 0]
    assert final_state['round'] == 20

def test_minimal_losing_game_has_one_fatal_error():
    def move0(b, s):
        if b.round == 1 and b._bot_index == 0:
            # trigger a bad move in the first round
            return (0, 0)
        else:
            return b.position
    def move1(b, s):
        return b.position

    l = maze_generator.generate_maze()
    final_state = run_game([move0, move1], max_rounds=20, layout_dict=l)
    assert final_state['gameover'] is True
    assert final_state['score'] == [0, 0]
    assert len(final_state['fatal_errors'][0]) == 1
    assert len(final_state['fatal_errors'][1]) == 0
    assert final_state['round'] == 1


def test_minimal_remote_game():
    def move(b, s):
        return b.position

    l = maze_generator.generate_maze()
    final_state = run_game(["test/demo01_stopping.py", move], max_rounds=20, layout_dict=l)
    final_state = run_game(["test/demo01_stopping.py", 'test/demo02_random.py'], max_rounds=20, layout_dict=l)
    assert final_state['gameover'] is True
    assert final_state['score'] == [0, 0]
    assert final_state['round'] == 20


def test_non_existing_file():
    l = maze_generator.generate_maze()
    res = run_game(["blah", "nothing"], max_rounds=1, layout_dict=l)
    print(res['fatal_errors'])

    # We might only catch only one of the errors
    assert len(res['fatal_errors'][0]) > 0 or len(res['fatal_errors'][1]) > 0
    if len(res['fatal_errors'][0]) > 0:
        assert res['fatal_errors'][0][0] == {
            'description': "ModuleNotFoundError: Could not load blah: No module named \'blah\'",
            'round': None,
            'turn': 0,
            'type': 'RemotePlayerFailure'
        }
    if len(res['fatal_errors'][1]) > 0:
        assert res['fatal_errors'][1][0] == {
            'description': "ModuleNotFoundError: Could not load nothing: No module named \'nothing\'",
            'round': None,
            'turn': 1,
            'type': 'RemotePlayerFailure'
        }

# TODO: Get it working again on Windows
@pytest.mark.skipif(_mswindows, reason="Test fails on some Python versions.")
def test_remote_errors(tmp_path):
    # TODO: Change error messages to be more meaningful

    syntax_error = FIXTURE_DIR / 'player_syntax_error'
    import_error = FIXTURE_DIR / 'player_import_error'

    l = maze_generator.generate_maze()

    res = run_game([str(syntax_error), str(import_error)], layout_dict=l, max_rounds=20)
    print(res['fatal_errors'])

    # We might only catch only one of the errors
    assert len(res['fatal_errors'][0]) > 0 or len(res['fatal_errors'][1]) > 0
    if len(res['fatal_errors'][0]) > 0:
        # Error messages have changed in Python 3.10. We can only do approximate matching
        assert "SyntaxError" in res['fatal_errors'][0][0].pop('description')
        assert res['fatal_errors'][0][0] == {
            'round': None,
            'turn': 0,
            'type': 'RemotePlayerFailure'
        }

    if len(res['fatal_errors'][1]) > 0:
        assert "ModuleNotFoundError" in res['fatal_errors'][1][0].pop('description')
        assert res['fatal_errors'][1][0] == {
            'round': None,
            'turn': 1,
            'type': 'RemotePlayerFailure'
        }

    # Both teams fail during setup: FAILURE
    assert res['game_phase'] == "FAILURE"
    assert res['gameover'] is True
    assert res['whowins'] == -1

    res = run_game(["0", str(import_error)], layout_dict=l, max_rounds=20)
    # Error messages have changed in Python 3.10. We can only do approximate matching
    assert "ModuleNotFoundError" in res['fatal_errors'][1][0].pop('description')
    assert res['fatal_errors'][1][0] == {
        'round': None,
        'turn': 1,
        'type': 'RemotePlayerFailure'
    }
    assert res['game_phase'] == "FAILURE"
    assert res['gameover'] is True
    assert res['whowins'] == -1

    res = run_game([str(import_error), "1"], layout_dict=l, max_rounds=20)
    # Error messages have changed in Python 3.10. We can only do approximate matching
    assert "ModuleNotFoundError" in res['fatal_errors'][0][0].pop('description')
    assert res['fatal_errors'][0][0] == {
        'round': None,
        'turn': 0,
        'type': 'RemotePlayerFailure'
    }
    assert res['game_phase'] == "FAILURE"
    assert res['gameover'] is True
    assert res['whowins'] == -1

@pytest.mark.parametrize('team_to_test', [0, 1])
def test_bad_move_function(team_to_test):
    """ Test that having a move function that returns a bad type
    appends a FatalException. """

    def stopping(b, state):
        return b.position
    def move0(b, state):
        return None
    def move1(b, state):
        return 0
    def move3(b, state):
        return 0, 0, 0
    def move4(b): # TypeError: move4() takes 1 positional argument but 2 were given
        return (0, 0), 0

    l = maze_generator.generate_maze()

    def test_run_game(move):
        # Flips the order of the teams depending on team_to_test
        if team_to_test == 0:
            teams = [move, stopping]
        elif team_to_test == 1:
            teams = [stopping, move]
        return run_game(teams, layout_dict=l, max_rounds=10)

    res = test_run_game(stopping)
    assert res['gameover']
    assert res['whowins'] == 2
    assert res['fatal_errors'] == [[], []]

    other = 1 - team_to_test

    res = test_run_game(move0)
    assert res['gameover']
    assert res['whowins'] == other
    assert res['fatal_errors'][team_to_test][0]['type'] == 'ValueError'
    assert res['fatal_errors'][team_to_test][0]['description'] == "Function move did not return a valid position: got 'None' instead."

    res = test_run_game(move1)
    assert res['gameover']
    assert res['whowins'] == other
    assert res['fatal_errors'][team_to_test][0]['type'] == 'ValueError'
    assert res['fatal_errors'][team_to_test][0]['description'] == "Function move did not return a valid position: got '0' instead."

    res = test_run_game(move3)
    assert res['gameover']
    assert res['whowins'] == other
    assert res['fatal_errors'][team_to_test][0]['type'] == 'ValueError'
    assert res['fatal_errors'][team_to_test][0]['description'] == "Function move did not return a valid position: got '(0, 0, 0)' instead."

    res = test_run_game(move4)
    assert res['gameover']
    assert res['whowins'] == other
    assert res['fatal_errors'][team_to_test][0]['type'] == 'TypeError'
    assert "takes 1 positional argument but 2 were given" in res['fatal_errors'][team_to_test][0]['description']


def test_setup_game_run_game_have_same_args():
    # We want to ensure that setup_game and run_game provide
    # the same API.

    # check that the parameters are the same
    params_setup_game = inspect.signature(setup_game).parameters.keys()
    params_run_game = inspect.signature(run_game).parameters.keys()
    assert params_setup_game == params_run_game

    # As run_game calls setup_game, we want to ensure that if a default is given
    # in both setup_game and run_game it has the same value in both lists.
    common_defaults = setup_game.__kwdefaults__.keys() & run_game.__kwdefaults__.keys()
    for kwarg in common_defaults:
        assert setup_game.__kwdefaults__[kwarg] == run_game.__kwdefaults__[kwarg], f"Default values for {kwarg} are different"


@pytest.mark.parametrize('bot_to_move', range(4))
# all combinations of True False in a list of 4
@pytest.mark.parametrize('bot_was_killed_flags', itertools.product(*[(True, False)] * 4))
def test_apply_move_resets_bot_was_killed(game_state, bot_to_move, bot_was_killed_flags):
    """ Check that `prepare_bot_state` sees the proper bot_was_killed flag
    and that `apply_move` will reset the flag to False. """
    team_id = bot_to_move % 2
    other_bot = (bot_to_move + 2) % 4
    other_team_id = 1 - team_id

    # specify which bot should move
    game_state['turn'] = bot_to_move

    bot_was_killed_flags = list(bot_was_killed_flags) # needs to be a list
    game_state['bot_was_killed'] = bot_was_killed_flags[:] # copy to avoid reference issues

    # create bot state for current turn
    current_bot_position = game_state['bots'][bot_to_move]
    bot_state = game.prepare_bot_state(game_state)

    # bot state should have proper bot_was_killed flag
    assert bot_state['bot_was_killed'] == bot_was_killed_flags

    # apply a dummy move that should reset bot_was_killed for the current bot
    _new_test_state = game.apply_move(game_state, current_bot_position)

    # the bot_was_killed flag should be False again
    assert game_state['bot_was_killed'][bot_to_move] is False

    # the bot_was_killed flags for other bot should still be as before
    assert game_state['bot_was_killed'][other_bot] == bot_was_killed_flags[other_bot]

    # all bot_was_killed flags for other team should still be as before
    assert game_state['bot_was_killed'][other_team_id::2] == bot_was_killed_flags[other_team_id::2]


def test_bot_does_not_eat_own_food():
    test_layout = """
        ######
        #a .y#
        #.bx #
        ######
    """
    teams = [
        stepping_player('v', '<'),
        stepping_player('^', '<')
    ]
    state = setup_game(teams, layout_dict=parse_layout(test_layout), max_rounds=2)
    assert state['bots'] == [(1, 1), (3, 2), (2, 2), (4, 1)]
    assert state['food'] == [{(1, 2)}, {(3, 1)}]
    for i in range(4):
        state = play_turn(state)
    assert state['bots'] == [(1, 2), (3, 1), (1, 2), (3, 1)]
    assert state['food'] == [{(1, 2)}, {(3, 1)}]


def test_suicide_win():
    # Test how a bot eats a food pellet that the enemy sits on
    # Since it is the last pellet, the game will end directly
    test_layout = """
        ######
        #a .x#
        #.   #
        #b  y#
        ######
    """
    teams = [
        stepping_player('>>', '--'),
        stepping_player('<-', '--')
    ]
    state = setup_game(teams, layout_dict=parse_layout(test_layout), max_rounds=2)
    assert state['bots'] == [(1, 1), (4, 1), (1, 3), (4, 3)]
    assert state['food'] == [{(1, 2)}, {(3, 1)}]
    # play until finished
    state = run_game(teams, layout_dict=parse_layout(test_layout), max_rounds=2)
    # bot 0 has been reset
    assert state['bots'] == [(1, 2), (3, 1), (1, 3), (4, 3)]
    assert state['food'] == [{(1, 2)}, set()]
    assert state['gameover'] is True
    assert state['whowins'] == 1
    assert state['round'] == 2
    assert state['turn'] == 0
    assert state['score'] == [1, game.KILL_POINTS]


def test_double_suicide():
    # Test how a bot can be killed when it runs into two bots
    test_layout = """
        ######
        # bx #
        #. y.#
        ######
    """
    teams = [
        stepping_player('-', '-'),
        stepping_player('<', '-')
    ]
    state = setup_game(teams, layout_dict=parse_layout(test_layout, bots={'a':(2,1)}),
            max_rounds=2)
    assert state['bots'] == [(2, 1), (3, 1), (2, 1), (3, 2)]
    assert state['food'] == [{(1, 2)}, {(4, 2)}]
    # play a two turns so that 1 moves
    state = play_turn(state)
    state = play_turn(state)
    # bot 1 has been reset
    assert state['bots'] == [(2, 1), (4, 2), (2, 1), (3, 2)]
    assert state['food'] == [{(1, 2)}, {(4, 2)}]
    assert state['gameover'] is False
    assert state['round'] == 1
    assert state['turn'] == 1
    # only a single KILL_POINT has been given
    assert state['score'] == [game.KILL_POINTS, 0]


def test_remote_game_closes_players_on_exit():
    l = maze_generator.generate_maze()

    # run a remote demo game with "0" and "1"
    state = run_game(["0", "1"], layout_dict=l, max_rounds=20, raise_bot_exceptions=True)
    assert state["gameover"]
    # Check that both processes have exited
    assert state["teams"][0].proc.wait(timeout=3) == 0
    assert state["teams"][1].proc.wait(timeout=3) == 0


def test_manual_remote_game_closes_players():
    l = maze_generator.generate_maze()

    # run a remote demo game with "0" and "1"
    state = setup_game(["0", "1"], layout_dict=l, max_rounds=10, raise_bot_exceptions=True)
    assert not state["gameover"]
    while not state["gameover"]:
        # still running
        # still running
        assert state["teams"][0].proc.poll() is None
        assert state["teams"][1].proc.poll() is None
        state = play_turn(state)

    # Check that both processes have exited
    assert state["teams"][0].proc.wait(timeout=3) == 0
    assert state["teams"][1].proc.wait(timeout=3) == 0


def test_invalid_setup_game_closes_players():
    l = maze_generator.generate_maze()

    # setup a remote demo game with "0" and "1" but bad max rounds
    state = setup_game(["0", "1"], layout_dict=l, max_rounds=0, raise_bot_exceptions=True)
    assert state["game_phase"] == "FAILURE"
    # Check that both processes have exited
    assert state["teams"][0].proc.wait(timeout=3) == 0
    assert state["teams"][1].proc.wait(timeout=3) == 0

def test_raises_and_exits_cleanly():
    l = layout.parse_layout(small_layout)

    path = FIXTURE_DIR / "player_move_division_by_zero"
    state = setup_game([str(path), "1"], layout_dict=l, max_rounds=2)
    with pytest.raises(PelitaBotError):
        while not state["gameover"]:
            state = play_turn(state, raise_bot_exceptions=True)

    # Game state is updated before the exception is raised
    assert state["gameover"] is True
    assert state["fatal_errors"][0][0]["type"] == "ZeroDivisionError"
    # Check that both processes have exited
    assert state["teams"][0].proc.wait(timeout=3) == 0
    assert state["teams"][1].proc.wait(timeout=3) == 0


@pytest.mark.parametrize('move_request, expected_prev, expected_req, expected_success', [
    # invalid moves (wrong types)
    # invalid moves end the game immediately, but the viewer will still interpret
    # the outcome of requested_moves, which is the reason we should test this
    (None,          (1, 1), None, False),
    (-1,            (1, 1), None, False),
    ((-1,),         (1, 1), None, False),
    ((-1, 1, 2),    (1, 1), None, False),
    ("a" ,          (1, 1), None, False),
    # not in maze
    ((-1, 2),       (1, 1), (-1, 2), False),
    # on wall
    ((2, 1),        (1, 1), (2, 1), False),
    # good move
    ((1, 2),        (1, 1), (1, 2), True),
    ]
)
def test_requested_moves(move_request, expected_prev, expected_req, expected_success):
    # test the possible return values of gamestate['requested_moves']
    test_layout = """
        ######
        #a#.y#
        #.bx #
        ######
    """
    def move(bot, state):
        return move_request
    teams = [
        move,
        stopping_player
    ]
    state = setup_game(teams, layout_dict=parse_layout(test_layout), max_rounds=2)
    assert state['requested_moves'] == [None, None, None, None]
    state = play_turn(state)
    assert state['requested_moves'][1:] == [None, None, None]
    assert state['requested_moves'][0] == {'previous_position': (1, 1), 'requested_position': expected_req, 'success': expected_success}
