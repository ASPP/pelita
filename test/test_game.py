"""Tests for Pelita game module"""
import pytest

from contextlib import contextmanager
import inspect
import itertools
import os
from pathlib import Path
import random
from textwrap import dedent
import time

from pelita import game, layout
from pelita.game import initial_positions, get_legal_positions, apply_move, run_game, setup_game, play_turn
from pelita.player import stepping_player


@contextmanager
def temp_wd(path):
    """ Temporarily change the working directory to path. """
    old = os.getcwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(old)


def test_initial_positions_basic():
    """Checks basic example for initial positions"""
    simple_layout = """
    ########
    # ###  #
    #      #
    ########
    """
    walls = layout.parse_layout(simple_layout)['walls']
    out = initial_positions(walls)
    exp = [(1, 1), (6, 2), (1, 2), (6, 1)]
    assert len(out) == 4
    assert out == exp


@pytest.mark.parametrize('simple_layout', [
    # We use these test layouts to check that our algorithm finds
    # the expected initial position. This is noted by the location
    # of the respective bots in the layout.
    """
    ########
    #0### 3#
    #2    1#
    ########
    """,
    """
    ########
    ##### 3#
    #20   1#
    ########
    """,
    """
    ########
    #0###13#
    #2    ##
    ########
    """,
    """
    ########
    #####1##
    ##20  3#
    ########
    """,
    # very degenerate case: 0 and 1 would start on the same field
    # we don’t expect any sensible layout to be this way
    """
    ########
    #####1##
    #####23#
    ########

    ########
    #####0##
    #####  #
    ########
    """,
    # similarly degenerate case: 2 starts in the enemy’s homezone,
    # even though there would still be space in its own homezone
    # TODO: The initial position algorithm could be adapted to
    # prefer the homezones before going to other territory
    # (this will reduce awkward respawn situations).
    """
    ########
    #    1##
    #0### 3#
    #### ###
    #### ###
    #### ###
    ##### ##
    #####2 #
    ########
    """,
    ])
def test_initial_positions(simple_layout):
    parsed = layout.parse_layout(simple_layout)
    i_pos = initial_positions(parsed['walls'])
    expected = parsed['bots']
    assert len(i_pos) == 4
    assert i_pos == expected


@pytest.mark.parametrize('bad_layout', [
    # not enough free spaces
    """
    ########
    #####0##
    ########
    """,
    """
    ########
    ##1#####
    ########
    """,
    # TODO: Should this even be a valid layout?
    """
    ########
    ########
    ########
    ########
    """,
])
def test_no_initial_positions_possible(bad_layout):
    parsed = layout.parse_layout(bad_layout)
    with pytest.raises(ValueError): # TODO should probably already raise in parse_layout
        initial_positions(parsed['walls'])


@pytest.mark.parametrize('layout_t', [layout.get_random_layout() for _ in range(30)])
def test_initial_positions_same_in_layout_random(layout_t):
    """Check initial positions are the same as what the layout says for 30 random layouts"""
    layout_name, layout_string = layout_t # get_random_layout returns a tuple of name and string
    parsed_l = layout.parse_layout(layout_string)
    exp = parsed_l["bots"]
    walls = parsed_l["walls"]
    out = initial_positions(walls)
    assert out == exp

@pytest.mark.parametrize('layout_name', layout.get_available_layouts())
def test_initial_positions_same_in_layout(layout_name):
    """Check initial positions are the same as what the layout says for all layouts"""
    l = layout.get_layout_by_name(layout_name=layout_name)
    parsed_l = layout.parse_layout(l)
    exp = parsed_l["bots"]
    walls = parsed_l["walls"]
    out = initial_positions(walls)
    assert out == exp

def test_get_legal_positions_basic():
    """Check that the output of legal moves contains all legal moves for one example layout"""
    l = layout.get_layout_by_name(layout_name="small_100")
    parsed_l = layout.parse_layout(l)
    legal_positions = get_legal_positions(parsed_l["walls"], parsed_l["bots"][0])
    exp = [(1, 4), (1, 6), (1, 5)]
    assert legal_positions == exp

@pytest.mark.parametrize('layout_t', [layout.get_random_layout() for _ in range(50)])
@pytest.mark.parametrize('bot_idx', (0, 1, 2, 3))
def test_get_legal_positions_random(layout_t, bot_idx):
    """Check that the output of legal moves returns only moves that are 1 field away and not inside a wall"""
    layout_name, layout_string = layout_t # get_random_layout returns a tuple of name and string
    parsed_l = layout.parse_layout(layout_string)
    bot = parsed_l["bots"][bot_idx]
    legal_positions = get_legal_positions(parsed_l["walls"], bot)
    for move in legal_positions:
        assert move not in parsed_l["walls"]
        assert  abs((move[0] - bot[0])+(move[1] - bot[1])) <= 1


# All combinations of bots that can be switched on/off
@pytest.mark.parametrize('bots_hidden', itertools.product(*[(True, False)] * 4))
def test_setup_game_bad_number_of_bots(bots_hidden):
    """ setup_game should fail when a wrong number of bots is given. """
    test_layout = """
        ##################
        #0#.  .  # .     #
        #2#####    #####3#
        #     . #  .  .#1#
        ################## """
    # remove bot x when bots_hidden[x] is True
    for x in range(4):
        if bots_hidden[x]:
            test_layout = test_layout.replace(str(x), ' ')
    parsed_layout = layout.parse_layout(test_layout)

    # dummy player
    stopping = lambda bot, s: (bot.position, s)

    if list(bots_hidden) == [False] * 4:
        # no bots are hidden. it should succeed
        setup_game([stopping, stopping], layout_dict=parsed_layout, max_rounds=10)
    else:
        with pytest.raises(ValueError):
            setup_game([stopping, stopping], layout_dict=parsed_layout, max_rounds=10)


@pytest.mark.parametrize('turn', (0, 1, 2, 3))
def test_play_turn_apply_error(turn):
    """check that quits when there are too many errors"""
    game_state = setup_random_basic_gamestate()
    error_dict = {
        "reason": 'illegal move',
        "bot_position": (1, 2)
    }
    game_state["turn"] = turn
    team = turn % 2
    game_state["errors"] = [{(r, t): error_dict for r in (1, 2) for t in (0, 1)},
                            {(r, t): error_dict for r in (1, 2) for t in (0, 1)}]
    # we pretend that two rounds have already been played
    # so that the error dictionaries are sane
    game_state["round"] = 3

    illegal_position = game_state["walls"][0]
    game_state_new = apply_move(game_state, illegal_position)
    assert game_state_new["gameover"]
    assert len(game_state_new["errors"][team]) == 5
    assert game_state_new["whowins"] == int(not team)
    assert set(game_state_new["errors"][team][(3, turn)].keys()) == set(["reason", "bot_position"])

@pytest.mark.parametrize('turn', (0, 1, 2, 3))
def test_play_turn_fatal(turn):
    """Checks that game quite after fatal error"""
    game_state = setup_random_basic_gamestate()
    game_state["turn"] = turn
    team = turn % 2
    fatal_list = [{}, {}]
    fatal_list[team] = {"error":True}
    game_state["fatal_errors"] = fatal_list
    move = get_legal_positions(game_state["walls"], game_state["bots"][turn])
    game_state_new = apply_move(game_state, move[0])
    assert game_state_new["gameover"]
    assert game_state_new["whowins"] == int(not team)

@pytest.mark.parametrize('turn', (0, 1, 2, 3))
def test_play_turn_illegal_position(turn):
    """check that illegal moves are added to error dict and bot still takes move"""
    game_state = setup_random_basic_gamestate()
    game_state["turn"] = turn
    team = turn % 2
    illegal_position = game_state["walls"][0]
    game_state_new = apply_move(game_state, illegal_position)
    assert len(game_state_new["errors"][team]) == 1
    assert game_state_new["errors"][team][(1, turn)].keys() == set(["reason", "bot_position"])
    assert game_state_new["bots"][turn] in get_legal_positions(game_state["walls"], game_state["bots"][turn])

@pytest.mark.parametrize('turn', (0, 1, 2, 3))
@pytest.mark.parametrize('which_food', (0, 1))
def test_play_turn_eating_enemy_food(turn, which_food):
    """Check that you eat enemy food but not your own"""
    ### 012345678901234567
    #0# ##################
    #1# #. ... .##.     3#
    #2# # # #  .  .### #1#
    #3# # # ##.   .      #
    #4# #      .   .## # #
    #5# #0# ###.  .  # # #
    #6# #2     .##. ... .#
    #7# ##################
    game_state = setup_specific_basic_gamestate(round=0, turn=turn)
    team = turn % 2
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
def test_play_turn_killing(turn):
    """Check that you can kill enemies but not yourself"""
    ### 012345678901234567
    #0# ##################
    #1# #. ... .##.     3#
    #2# # # #  .  .### #1#
    #3# # # ##.   .      #
    #4# #      .   .## # #
    #5# #0# ###.  .  # # #
    #6# #2     .##. ... .#
    #7# ##################
    game_state = setup_specific_basic_gamestate()
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
def test_play_turn_friendly_fire(setups):
    """Check that you can kill enemies but not yourself"""
    ### 012345678901234567
    #0# ##################
    #1# #. ... .##.     3#
    #2# # # #  .  .### #1#
    #3# # # ##.   .      #
    #4# #      .   .## # #
    #5# #0# ###.  .  # # #
    #6# #2     .##. ... .#
    #7# ##################
    game_state = setup_specific_basic_gamestate()
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
    # 210  #
    ########

    ########
    #  ..  #
    #  3   #
    ########
    """

    l1 = """
    ########
    #  ..  #
    #  103 #
    ########

    ########
    #  ..  #
    #   2  #
    ########
    """
    # dummy bots
    stopping = lambda bot, s: (bot.position, s)

    parsed_l0 = layout.parse_layout(l0)
    for bot in (0, 2):
        game_state = setup_game([stopping, stopping], layout_dict=parsed_l0)

        game_state['turn'] = bot
        # get position of bots 1 (and 3)
        kill_position = game_state['bots'][1]
        assert kill_position == game_state['bots'][3]
        new_state = apply_move(game_state, kill_position)
        # team 0 scores twice
        assert new_state['score'] == [10, 0]
        # bots 1 and 3 are back to origin
        assert new_state['bots'][1::2] == [(6, 2), (6, 1)]

    parsed_l1 = layout.parse_layout(l1)
    for bot in (1, 3):
        game_state = setup_game([stopping, stopping], layout_dict=parsed_l1)

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
    #3210  #
    ########
    """

    l1 = """
    ########
    #  ..  #
    #  1032#
    ########
    """
    # dummy bots
    stopping = lambda bot, s: (bot.position, s)

    parsed_l0 = layout.parse_layout(l0)
    for bot in (1, 3):
        game_state = setup_game([stopping, stopping], layout_dict=parsed_l0)

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

    parsed_l1 = layout.parse_layout(l1)
    for bot in (0, 2):
        game_state = setup_game([stopping, stopping], layout_dict=parsed_l1)

        game_state['turn'] = bot
        # get position of bot 3
        suicide_position = game_state['bots'][3]
        new_state = apply_move(game_state, suicide_position)
        # team 0 scores
        assert new_state['score'] == [0, 5]


def test_cascade_kill():
    cascade = [
    """
    ########
    #1 ..30#
    #     2#
    ########
    """,
    """
    ########
    #0 .. 3#
    #     2#
    ########

    ########
    #1 ..  #
    #      #
    ########
    """,
    """
    ########
    #0 .. 3#
    #     1#
    ########

    ########
    #  ..  #
    #     2#
    ########
    """,
    """
    ########
    #0 .. 3#
    #2    1#
    ########
    """
    ]
    def move(bot, state):
        if not bot.is_blue and bot.turn == 1 and bot.round == 1:
            return (6, 1), state
        return bot.position, state
    layouts = [layout.parse_layout(l) for l in cascade]
    state = setup_game([move, move], max_rounds=5, layout_dict=layout.parse_layout(cascade[0]))
    assert state['bots'] == layouts[0]['bots']
    state = game.play_turn(state) # Bot 0 stands
    assert state['bots'] == layouts[0]['bots']
    state = game.play_turn(state) # Bot 1 stands
    state = game.play_turn(state) # Bot 2 stands
    state = game.play_turn(state) # Bot 3 moves, kills 0. Bot 0 and 1 are on same spot
    assert state['bots'] == layouts[1]['bots']
    state = game.play_turn(state) # Bot 0 stands, kills 1. Bot 1 and 2 are on same spot
    assert state['bots'] == layouts[2]['bots']
    state = game.play_turn(state) # Bot 1 stands, kills 2.
    assert state['bots'] == layouts[3]['bots']


def test_cascade_kill_2():
    """ Checks that killing occurs only for the bot whose turn it is
    or for any bot that this bot moves onto.
    If a bot respawns on an enemy, it will only be killed when it is its own
    or the enemy’s turn (and neither of them moves).
    """
    cascade = [
    """
    ########
    #30.. 2#
    #1     #
    ########
    """,
    """
    ########
    #0 .. 2#
    #1     #
    ########

    ########
    #  .. 3#
    #      #
    ########
    """,
    """
    ########
    #0 .. 3#
    #1     #
    ########

    ########
    #  ..  #
    #2     #
    ########
    """,
    """
    ########
    #0 .. 3#
    #2    1#
    ########
    """
    ]
    def move(bot, state):
        if bot.is_blue and bot.turn == 0 and bot.round == 1:
            return (1, 1), state
        return bot.position, state
    layouts = [layout.parse_layout(l) for l in cascade]
    state = setup_game([move, move], max_rounds=5, layout_dict=layout.parse_layout(cascade[0]))
    assert state['bots'] == layouts[0]['bots']
    state = game.play_turn(state) # Bot 0 moves, kills 3. Bot 2 and 3 are on same spot
    assert state['bots'] == layouts[1]['bots']
    state = game.play_turn(state) # Bot 1 stands. Bot 2 and 3 are on same spot
    assert state['bots'] == layouts[1]['bots']
    state = game.play_turn(state) # Bot 2 stands, gets killed. Bot 1 and 2 are on same spot
    assert state['bots'] == layouts[2]['bots']
    state = game.play_turn(state) # Bot 3 stands. Bot 1 and 2 are on same spot
    assert state['bots'] == layouts[2]['bots']
    state = game.play_turn(state) # Bot 0 stands. Bot 1 and 2 are on same spot
    assert state['bots'] == layouts[2]['bots']
    state = game.play_turn(state) # Bot 1 stands, kills 2.
    assert state['bots'] == layouts[3]['bots']


def test_cascade_kill_rescue_1():
    """ Checks that killing occurs only for the bot whose turn it is
    or for any bot that this bot moves onto.
    If a bot respawns on an enemy, it will only be killed when it is its own
    or the enemy’s turn (and neither of them moves).
    If bot moves before it is the enemy’s turn. Bot is rescued.
    """
    cascade = [
    """
    ########
    #30.. 2#
    #1     #
    ########
    """,
    """
    ########
    #0 .. 2#
    #1     #
    ########

    ########
    #  .. 3#
    #      #
    ########
    """,
    """
    ########
    #0 ..23#
    #1     #
    ########
    """
    ]
    def move(bot, state):
        if bot.is_blue and bot.turn == 0 and bot.round == 1:
            return (1, 1), state
        if bot.is_blue and bot.turn == 1 and bot.round == 1:
            return (5, 1), state
        return bot.position, state
    layouts = [layout.parse_layout(l) for l in cascade]
    state = setup_game([move, move], max_rounds=5, layout_dict=layout.parse_layout(cascade[0]))
    assert state['bots'] == layouts[0]['bots']
    state = game.play_turn(state) # Bot 0 moves, kills 3. Bot 2 and 3 are on same spot
    assert state['bots'] == layouts[1]['bots']
    state = game.play_turn(state) # Bot 1 stands. Bot 2 and 3 are on same spot
    assert state['bots'] == layouts[1]['bots']
    state = game.play_turn(state) # Bot 2 moves. Rescues itself
    assert state['bots'] == layouts[2]['bots']


def test_cascade_kill_rescue_2():
    """ Checks that killing occurs only for the bot whose turn it is
    or for any bot that this bot moves onto.
    If a bot respawns on an enemy, it will only be killed when it is its own
    or the enemy’s turn (and neither of them moves).
    If enemy moves before it is the bot’s turn. Bot is rescued.
    """
    cascade = [
    """
    ########
    #3 ..  #
    #10   2#
    ########
    """,
    """
    ########
    #3 ..  #
    #0    1#
    ########

    ########
    #  ..  #
    #     2#
    ########
    """,
    """
    ########
    #3 ..  #
    #0   12#
    ########
    """
    ]
    def move(bot, state):
        if bot.is_blue and bot.turn == 0 and bot.round == 1:
            return (1, 2), state
        if not bot.is_blue and bot.turn == 0 and bot.round == 1:
            return (5, 2), state
        return bot.position, state
    layouts = [layout.parse_layout(l) for l in cascade]
    state = setup_game([move, move], max_rounds=5, layout_dict=layout.parse_layout(cascade[0]))
    assert state['bots'] == layouts[0]['bots']
    state = game.play_turn(state) # Bot 0 moves, kills 1. Bot 1 and 2 are on same spot
    assert state['bots'] == layouts[1]['bots']
    state = game.play_turn(state) # Bot 1 moves. Bot 2 is rescued.
    assert state['bots'] == layouts[2]['bots']


def test_cascade_suicide():
    cascade = [
    """
    ########
    #1 ..03#
    #     2#
    ########
    """,
    """
    ########
    #0 .. 3#
    #     2#
    ########

    ########
    #1 ..  #
    #      #
    ########
    """,
    """
    ########
    #0 .. 3#
    #     1#
    ########

    ########
    #  ..  #
    #     2#
    ########
    """,
    """
    ########
    #0 .. 3#
    #2    1#
    ########
    """
    ]
    def move(bot, state):
        if bot.is_blue and bot.turn == 0 and bot.round == 1:
            return (6, 1), state
        return bot.position, state
    layouts = [layout.parse_layout(l) for l in cascade]
    state = setup_game([move, move], max_rounds=5, layout_dict=layout.parse_layout(cascade[0]))
    assert state['bots'] == layouts[0]['bots']
    state = game.play_turn(state) # Bot 0 moves onto 3. Gets killed. Bot 0 and 1 are on same spot.
    assert state['bots'] == layouts[1]['bots']
    state = game.play_turn(state) # Bot 1 moves, gets killed. Bot 1 and 2 are on same spot
    assert state['bots'] == layouts[2]['bots']
    state = game.play_turn(state) # Bot 2 moves, gets killed.
    assert state['bots'] == layouts[3]['bots']


def test_moving_through_maze():
    test_start = """
        ######
        #0 . #
        #.. 1#
        #2  3#
        ###### """
    parsed = layout.parse_layout(test_start)
    teams = [
        stepping_player('>-v>>>-', '-^^->->'),
        stepping_player('<<-<<<-', '-------')
    ]
    state = setup_game(teams, layout_dict=parsed, max_rounds=8)

    # play first round
    for i in range(4):
        state = game.play_turn(state)
    test_first_round = layout.parse_layout(
        """ ######
            # 0. #
            #..1 #
            #2  3#
            ###### """)

    assert test_first_round['bots'] == state['bots']
    assert test_first_round['food'] == list(state['food'][0]) + list(state['food'][1])
    assert state['score'] == [0, 0]

    for i in range(4):
        state = game.play_turn(state)
    test_second_round = layout.parse_layout(
        """ ######
            #  . #
            #.   #
            #    #
            ######
            ######
            # 0  #
            #21  #
            #   3#
            ###### """)

    assert test_second_round['bots'] == state['bots']
    assert test_second_round['food'] == list(state['food'][0]) + list(state['food'][1])
    assert state['score'] == [0, 1]

    for i in range(4):
        state = game.play_turn(state)
    test_third_round = layout.parse_layout(
        """ ######
            #2 . #
            #.0 1#
            #   3#
            ###### """)

    assert test_third_round['bots'] == state['bots']
    assert test_third_round['food'] == list(state['food'][0]) + list(state['food'][1])
    assert state['score'] == [game.KILL_POINTS, 1]

    for i in range(4):
        state = game.play_turn(state)
    test_fourth_round = layout.parse_layout(
        """ ######
            #  . #
            #.   #
            #    #
            ######
            ######
            #2   #
            #0 1 #
            #   3#
            ###### """)

    assert test_fourth_round['bots'] == state['bots']
    assert test_fourth_round['food'] == list(state['food'][0]) + list(state['food'][1])
    assert state['score'] == [game.KILL_POINTS, game.KILL_POINTS + 1]

    for i in range(4):
        state = game.play_turn(state)
    test_fifth_round = layout.parse_layout(
        """ ######
            #  . #
            #.   #
            #    #
            ######
            ######
            # 2  #
            # 0 1#
            #   3#
            ###### """)
    assert test_fifth_round['bots'] == state['bots']
    assert test_fifth_round['food'] == list(state['food'][0]) + list(state['food'][1])
    assert state['score'] == [game.KILL_POINTS * 2, game.KILL_POINTS + 1]

    for i in range(4):
        state = game.play_turn(state)
    test_sixth_round = layout.parse_layout(
        """ ######
            #  . #
            #.   #
            #    #
            ######
            ######
            # 2  #
            #0 1 #
            #   3#
            ###### """)

    assert test_sixth_round['bots'] == state['bots']
    assert test_sixth_round['food'] == list(state['food'][0]) + list(state['food'][1])
    assert state['score'] == [game.KILL_POINTS * 2, game.KILL_POINTS * 2+ 1]

    for i in range(3): # !! Only move three bots
        state = game.play_turn(state)

    test_seventh_round = layout.parse_layout(
        """ ######
            #    #
            #.   #
            #    #
            ######
            ######
            #  2 #
            #0 1 #
            #   3#
            ###### """)

    assert test_seventh_round['bots'] == state['bots']
    assert test_seventh_round['food'] == list(state['food'][0]) + list(state['food'][1])
    assert state['score'] == [game.KILL_POINTS * 2 + 1, game.KILL_POINTS * 2 + 1]
    assert state['gameover'] == True
    assert state['whowins'] == 2

    with pytest.raises(ValueError):
        state = game.play_turn(state)


@pytest.mark.parametrize('score', ([[3, 3], 2], [[1, 13], 1], [[13, 1], 0]))
def test_play_turn_maxrounds(score):
    """Check that game quits at maxrounds and choses correct winner"""
    # this works for ties as well, because there are no points to be gained at init positions
    game_state = setup_random_basic_gamestate()
    game_state["round"] = 301
    game_state["score"] = score[0]
    game_state_new = game.play_turn(game_state)
    assert game_state_new["gameover"]
    assert game_state_new["whowins"] == score[1]

def test_play_turn_move():
    """Checks that bot is moved to intended space"""
    turn = 0
    l = layout.get_layout_by_name("small_100")
    parsed_l = layout.parse_layout(l)
    game_state = {
        "food": parsed_l["food"],
        "walls": parsed_l["walls"],
        "bots": parsed_l["bots"],
        "max_rounds": 300,
        "team_names": ("a", "b"),
        "turn": turn,
        "round": 0,
        "timeout": [],
        "gameover": False,
        "whowins": None,
        "team_say": "bla",
        "score": 0,
        "kills":[0]*4,
        "deaths": [0]*4,
        "bot_was_killed": [False]*4,
        "errors": [[], []],
        "fatal_errors": [{}, {}],
        "rnd": random.Random()
        }
    legal_positions = get_legal_positions(game_state["walls"], game_state["bots"][turn])
    game_state_new = apply_move(game_state, legal_positions[0])
    assert game_state_new["bots"][turn] == legal_positions[0]



def setup_random_basic_gamestate(*, round=1, turn=0):
    """helper function for testing play turn"""
    l = layout.get_layout_by_name("small_100")
    parsed_l = layout.parse_layout(l)

    stopping = lambda bot, s: (bot.position, s)

    game_state = setup_game([stopping, stopping], layout_dict=parsed_l)
    game_state['round'] = round
    game_state['turn'] = turn
    return game_state


def setup_specific_basic_gamestate(round=0, turn=0):
    """helper function for testing play turn"""
    l = """
##################
#. ... .##.     3#
# # #  .  .### #1#
# # ##.   .      #
#      .   .## # #
#0# ###.  .  # # #
#2     .##. ... .#
##################
"""
    parsed_l = layout.parse_layout(l)

    stopping = lambda bot, s: (bot.position, s)

    game_state = setup_game([stopping, stopping], layout_dict=parsed_l)
    game_state['round'] = round
    game_state['turn'] = turn
    return game_state


def test_max_rounds():
    l = """
    ########
    #20..13#
    #      #
    ########
    """
    def move(bot, s):
        # in the first round (round #1),
        # all bots move to the south
        if bot.round == 1:
            # go one step to the right
            return (bot.position[0], bot.position[1] + 1), s
        else:
            # There should not be more then one round in this test
            raise RuntimeError("We should not be here in this test")

    l = layout.parse_layout(l)
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
        'type': 'FatalException',
        'description': 'Exception in client (RuntimeError): We should not be here in this test',
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


def test_last_round_check():
    # (max_rounds, current_round, turn): gameover
    test_map = {
        (1, None, None): False,
        (1, 1, 0): False,
        (1, 1, 3): True,
    }
    for test_val, test_res in test_map.items():
        max_rounds, current_round, current_turn = test_val
        state = {
            'max_rounds': max_rounds,
            'round': current_round,
            'turn': current_turn,
            'fatal_errors': [[],[]],
            'errors': [[],[]],
            'gameover': False,
            'score': [0, 0],
            'food': [{(1,1)}, {(1,1)}] # dummy food
        }
        res = game.check_gameover(state, detect_final_move=True)
        assert res['gameover'] == test_res


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
        (((0, 5), (0, 5)), 2),
        (((1, 0), (0, 0)), 1),
        (((0, 0), (1, 0)), 0),
        (((1, 0), (1, 0)), 2),
        (((1, 1), (1, 0)), 2),
        (((1, 0), (0, 5)), 1),
        (((0, 5), (1, 0)), 0),
    ]
)
def test_error_finishes_game(team_errors, team_wins):
    # the mapping is as follows:
    # [(num_fatal_0, num_errors_0), (num_fatal_1, num_errors_1), result_flag]
    # the result flag: 0/1: team 0/1 wins, 2: draw, False: no winner yet
    assert game.MAX_ALLOWED_ERRORS == 4, "Test assumes MAX_ALLOWED_ERRORS is 4"

    (fatal_0, errors_0), (fatal_1, errors_1) = team_errors
    # just faking a bunch of errors in our game state
    state = {
        "fatal_errors": [[None] * fatal_0, [None] * fatal_1],
        "errors": [[None] * errors_0, [None] * errors_1]
    }
    res = game.check_gameover(state)
    if team_wins is False:
        assert res["whowins"] is None
        assert res["gameover"] is False
    else:
        assert res["whowins"] == team_wins
        assert res["gameover"] is True


@pytest.mark.parametrize('bot_to_move', [0, 1, 2, 3])
def test_finished_when_no_food(bot_to_move):
    """ Test that the game is over when a team has eaten its food. """
    l = """
    ########
    #  0.2 #
    # 3.1  #
    ########
    """
    bot_turn = bot_to_move // 2
    team_to_move = bot_to_move % 2
    def move(bot, s):
        if team_to_move == 0 and bot.is_blue and bot_turn == bot._bot_turn:
            return (4, 1), s
            # eat the food between 0 and 2
        if team_to_move == 1 and (not bot.is_blue) and bot_turn == bot._bot_turn:
            # eat the food between 3 and 1
            return (3, 2), s
        return bot.position, s

    l = layout.parse_layout(l)
    final_state = run_game([move, move], layout_dict=l, max_rounds=20)
    assert final_state['round'] == 1
    assert final_state['turn'] == bot_to_move


def test_minimal_game():
    def move(b, s):
        return b.position, s

    layout_name, layout_string = layout.get_random_layout()
    l = layout.parse_layout(layout_string)
    final_state = run_game([move, move], max_rounds=20, layout_dict=l)
    assert final_state['gameover'] is True
    assert final_state['score'] == [0, 0]
    assert final_state['round'] == 20

def test_minimal_losing_game_has_one_error():
    def move0(b, s):
        if b.round == 1 and b._bot_index == 0:
            # trigger a bad move in the first round
            return (0, 0), s
        else:
            return b.position, s
    def move1(b, s):
        return b.position, s

    layout_name, layout_string = layout.get_random_layout()
    l = layout.parse_layout(layout_string)
    final_state = run_game([move0, move1], max_rounds=20, layout_dict=l)
    assert final_state['gameover'] is True
    assert final_state['score'] == [0, 0]
    assert len(final_state['errors'][0]) == 1
    assert len(final_state['errors'][1]) == 0
    assert final_state['round'] == 20


def test_minimal_remote_game():
    def move(b, s):
        return b.position, s

    layout_name, layout_string = layout.get_random_layout()
    l = layout.parse_layout(layout_string)
    final_state = run_game(["test/demo01_stopping.py", move], max_rounds=20, layout_dict=l)
    final_state = run_game(["test/demo01_stopping.py", 'test/demo02_random.py'], max_rounds=20, layout_dict=l)
    assert final_state['gameover'] is True
    assert final_state['score'] == [0, 0]
    assert final_state['round'] == 20


def test_non_existing_file():
    # TODO: Change error message to be more meaningful
    layout_name, layout_string = layout.get_random_layout()
    l = layout.parse_layout(layout_string)
    res = run_game(["blah", "nothing"], max_rounds=1, layout_dict=l)
    assert res['fatal_errors'][0][0] == {
        'description': '("Could not load blah: No module named \'blah\'", \'ModuleNotFoundError\')',
        'round': None,
        'turn': 0,
        'type': 'PlayerDisconnected'
    }

def test_remote_errors(tmp_path):
    # TODO: Change error messages to be more meaningful
    # we change to the tmp dir, to make our paths simpler
    syntax_error = dedent("""
    def move(b, state)
        return b.position, state
    """)
    import_error = dedent("""
    import does_not_exist
    def move(b, state):
        return b.position, state
    """)

    layout_name, layout_string = layout.get_random_layout()
    l = layout.parse_layout(layout_string)

    with temp_wd(tmp_path):
        s_py = Path("s.py")
        s_py.write_text(syntax_error)
        i_py = Path("i.py")
        i_py.write_text(import_error)

        res = run_game([str(s_py), str(i_py)], layout_dict=l, max_rounds=20)
        assert res['fatal_errors'][0][0] == {
            'description': "('Could not load s.py: invalid syntax (s.py, line 2)', 'SyntaxError')",
            'round': None,
            'turn': 0,
            'type': 'PlayerDisconnected'
        }
        # Both teams fail during setup: DRAW
        assert res['whowins'] == 2
        res = run_game(["0", str(i_py)], layout_dict=l, max_rounds=20)
        assert res['fatal_errors'][1][0] == {
            'description': '("Could not load i.py: No module named \'does_not_exist\'", \'ModuleNotFoundError\')',
            'round': None,
            'turn': 1,
            'type': 'PlayerDisconnected'
        }
        assert res['whowins'] == 0
        res = run_game([str(i_py), "1"], layout_dict=l, max_rounds=20)
        assert res['fatal_errors'][0][0] == {
            'description': '("Could not load i.py: No module named \'does_not_exist\'", \'ModuleNotFoundError\')',
            'round': None,
            'turn': 0,
            'type': 'PlayerDisconnected'
        }
        assert res['whowins'] == 1


@pytest.mark.parametrize('team_to_test', [0, 1])
def test_bad_move_function(team_to_test):
    """ Test that having a move function that returns a bad type
    appends a FatalException. """

    def stopping(b, state):
        return b.position, state
    def move0(b, state):
        return None
    def move1(b, state):
        return 0
    def move2(b, state):
        return 0, 0
    def move3(b, state):
        return 0, 0, 0
    def move4(b): # TypeError: move4() takes 1 positional argument but 2 were given
        return (0, 0), 0

    layout_name, layout_string = layout.get_random_layout()
    l = layout.parse_layout(layout_string)

    def test_run_game(move):
        # Flips the order of the teams depending on team_to_test
        if team_to_test == 0:
            teams = [move, stopping]
        elif team_to_test == 1:
            teams = [stopping, move]
        return run_game(teams, layout_dict=l, max_rounds=10)

    other = 1 - team_to_test

    res = test_run_game(move0)
    assert res['gameover']
    assert res['whowins'] == other
    assert res['fatal_errors'][team_to_test][0]['type'] == 'FatalException'
    assert res['fatal_errors'][team_to_test][0]['description'] == 'Exception in client (ValueError): Function move did not return move and state: got None instead.'

    res = test_run_game(move1)
    assert res['gameover']
    assert res['whowins'] == other
    assert res['fatal_errors'][team_to_test][0]['type'] == 'FatalException'
    assert res['fatal_errors'][team_to_test][0]['description'] == 'Exception in client (ValueError): Function move did not return move and state: got 0 instead.'

    res = test_run_game(move2)
    assert res['gameover']
    assert res['whowins'] == other
    assert res['fatal_errors'][team_to_test][0]['type'] == 'FatalException'
    assert res['fatal_errors'][team_to_test][0]['description'] == 'Exception in client (ValueError): Function move did not return a valid position: got 0 instead.'

    res = test_run_game(move3)
    assert res['gameover']
    assert res['whowins'] == other
    assert res['fatal_errors'][team_to_test][0]['type'] == 'FatalException'
    assert res['fatal_errors'][team_to_test][0]['description'] == 'Exception in client (ValueError): Function move did not return move and state: got (0, 0, 0) instead.'

    res = test_run_game(move4)
    assert res['gameover']
    assert res['whowins'] == other
    assert res['fatal_errors'][team_to_test][0]['type'] == 'FatalException'
    assert res['fatal_errors'][team_to_test][0]['description'] == 'Exception in client (TypeError): move4() takes 1 positional argument but 2 were given'


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
def test_apply_move_resets_bot_was_killed(bot_to_move, bot_was_killed_flags):
    """ Check that `prepare_bot_state` sees the proper bot_was_killed flag
    and that `apply_move` will reset the flag to False. """
    team_id = bot_to_move % 2
    other_bot = (bot_to_move + 2) % 4
    other_team_id = 1 - team_id

    # specify which bot should move
    test_state = setup_random_basic_gamestate(turn=bot_to_move)

    bot_was_killed_flags = list(bot_was_killed_flags) # needs to be a list
    test_state['bot_was_killed'] = bot_was_killed_flags[:] # copy to avoid reference issues

    # create bot state for current turn
    current_bot_position = test_state['bots'][bot_to_move]
    bot_state = game.prepare_bot_state(test_state)

    # bot state should have proper bot_was_killed flag
    assert bot_state['team']['bot_was_killed'] == bot_was_killed_flags[team_id::2]

    # apply a dummy move that should reset bot_was_killed for the current bot
    new_test_state = game.apply_move(test_state, current_bot_position)

    # the bot_was_killed flag should be False again
    assert test_state['bot_was_killed'][bot_to_move] == False

    # the bot_was_killed flags for other bot should still be as before
    assert test_state['bot_was_killed'][other_bot] == bot_was_killed_flags[other_bot]

    # all bot_was_killed flags for other team should still be as before
    assert test_state['bot_was_killed'][other_team_id::2] == bot_was_killed_flags[other_team_id::2]


def test_bot_does_not_eat_own_food():
    test_layout = """
        ######
        #0 .3#
        #.21 #
        ######
    """
    teams = [
        stepping_player('v', '<'),
        stepping_player('^', '<')
    ]
    state = setup_game(teams, layout_dict=layout.parse_layout(test_layout), max_rounds=2)
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
        #0 .1#
        #.   #
        #2  3#
        ######
    """
    teams = [
        stepping_player('>>', '--'),
        stepping_player('<-', '--')
    ]
    state = setup_game(teams, layout_dict=layout.parse_layout(test_layout), max_rounds=2)
    assert state['bots'] == [(1, 1), (4, 1), (1, 3), (4, 3)]
    assert state['food'] == [{(1, 2)}, {(3, 1)}]
    # play until finished
    state = run_game(teams, layout_dict=layout.parse_layout(test_layout), max_rounds=2)
    # bot 0 has been reset
    assert state['bots'] == [(1, 2), (3, 1), (1, 3), (4, 3)]
    assert state['food'] == [{(1, 2)}, set()]
    assert state['gameover'] == True
    assert state['whowins'] == 1
    assert state['round'] == 2
    assert state['turn'] == 0
    assert state['score'] == [1, game.KILL_POINTS]


def test_double_suicide():
    # Test how a bot can be killed when it runs into two bots
    test_layout = """
        ######
        # 01 #
        #.  .#
        ######

        ######
        # 2  #
        #. 3.#
        ######
    """
    teams = [
        stepping_player('-', '-'),
        stepping_player('<', '-')
    ]
    state = setup_game(teams, layout_dict=layout.parse_layout(test_layout), max_rounds=2)
    assert state['bots'] == [(2, 1), (3, 1), (2, 1), (3, 2)]
    assert state['food'] == [{(1, 2)}, {(4, 2)}]
    # play a two turns so that 1 moves
    state = play_turn(state)
    state = play_turn(state)
    # bot 1 has been reset
    assert state['bots'] == [(2, 1), (4, 2), (2, 1), (3, 2)]
    assert state['food'] == [{(1, 2)}, {(4, 2)}]
    assert state['gameover'] == False
    assert state['round'] == 1
    assert state['turn'] == 1
    # only a single KILL_POINT has been given
    assert state['score'] == [game.KILL_POINTS, 0]


def test_remote_game_closes_players_on_exit():
    layout_name, layout_string = layout.get_random_layout()
    l = layout.parse_layout(layout_string)

    # run a remote demo game with "0" and "1"
    state = run_game(["0", "1"], layout_dict=l, max_rounds=20, allow_exceptions=True)
    assert state["gameover"]
    # Check that both processes have exited
    assert state["teams"][0].proc[0].wait(timeout=3) == 0
    assert state["teams"][1].proc[0].wait(timeout=3) == 0


def test_manual_remote_game_closes_players():
    layout_name, layout_string = layout.get_random_layout()
    l = layout.parse_layout(layout_string)

    # run a remote demo game with "0" and "1"
    state = setup_game(["0", "1"], layout_dict=l, max_rounds=10, allow_exceptions=True)
    assert not state["gameover"]
    while not state["gameover"]:
        # still running
        # still running
        assert state["teams"][0].proc[0].poll() is None
        assert state["teams"][1].proc[0].poll() is None
        state = play_turn(state)

    # Check that both processes have exited
    assert state["teams"][0].proc[0].wait(timeout=3) == 0
    assert state["teams"][1].proc[0].wait(timeout=3) == 0


def test_invalid_setup_game_closes_players():
    layout_name, layout_string = layout.get_random_layout()
    l = layout.parse_layout(layout_string)

    # setup a remote demo game with "0" and "1" but bad max rounds
    state = setup_game(["0", "1"], layout_dict=l, max_rounds=0, allow_exceptions=True)
    assert state["gameover"]
    # Check that both processes have exited
    assert state["teams"][0].proc[0].wait(timeout=3) == 0
    assert state["teams"][1].proc[0].wait(timeout=3) == 0

