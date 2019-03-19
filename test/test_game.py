"""Tests for Pelita game module"""
import pytest

from pathlib import Path
import random

import numpy as np

from pelita import layout
from pelita.game import initial_positions, get_legal_moves, apply_move, run_game

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

small_test_layouts = [
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
    """]

@pytest.mark.parametrize('simple_layout', small_test_layouts)
def test_initial_positions(simple_layout):
    parsed = layout.parse_layout(simple_layout)
    i_pos = initial_positions(parsed['walls'])
    expected = parsed['bots']
    assert len(i_pos) == 4
    assert i_pos == expected


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

def test_get_legal_moves_basic():
    """Check that the output of legal moves contains all legal moves for one example layout"""
    l = layout.get_layout_by_name(layout_name="layout_small_without_dead_ends_100")
    parsed_l = layout.parse_layout(l)
    legal_moves = get_legal_moves(parsed_l["walls"], parsed_l["bots"][0])
    exp = [(2, 5), (1, 6), (1, 5)]
    assert legal_moves == exp

@pytest.mark.parametrize('layout_t', [layout.get_random_layout() for _ in range(50)])
@pytest.mark.parametrize('bot_idx', (0, 1, 2, 3))
def test_get_legal_moves_random(layout_t, bot_idx):
    """Check that the output of legal moves returns only moves that are 1 field away and not inside a wall"""
    layout_name, layout_string = layout_t # get_random_layout returns a tuple of name and string
    parsed_l = layout.parse_layout(layout_string)
    bot = parsed_l["bots"][bot_idx]
    legal_moves = get_legal_moves(parsed_l["walls"], bot)
    for move in legal_moves:
        assert move not in parsed_l["walls"]
        assert  abs((move[0] - bot[0])+(move[1] - bot[1])) <= 1


@pytest.mark.parametrize('turn', (0, 1, 2, 3))
def test_play_turn_apply_error(turn):
    """check that quits when there are too many errors"""
    game_state = setup_random_basic_gamestate()
    error_dict = {
        "turn": 0,
        "round": 0,
        "reason": 'illegal move',
        "bot_position": (1, 2)
    }
    game_state["turn"] = turn
    team = turn % 2
    game_state["errors"] = [[error_dict, error_dict, error_dict, error_dict],
                            [error_dict, error_dict, error_dict, error_dict]]
    illegal_move = game_state["walls"][0]
    game_state_new = apply_move(game_state, illegal_move)
    assert game_state_new["gameover"]
    assert len(game_state_new["errors"][team]) == 5
    assert game_state_new["whowins"] == int(not team)
    assert set(game_state_new["errors"][team][4].keys()) == set(["turn", "round", "reason", "bot_position"])

@pytest.mark.parametrize('turn', (0, 1, 2, 3))
def test_play_turn_fatal(turn):
    """Checks that game quite after fatal error"""
    game_state = setup_random_basic_gamestate()
    game_state["turn"] = turn
    team = turn % 2
    fatal_list = [{}, {}]
    fatal_list[team] = {"error":True}
    game_state["fatal_errors"] = fatal_list
    move = get_legal_moves(game_state["walls"], game_state["bots"][turn])
    game_state_new = apply_move(game_state, move[0])
    assert game_state_new["gameover"]
    assert game_state_new["whowins"] == int(not team)

@pytest.mark.parametrize('turn', (0, 1, 2, 3))
def test_play_turn_illegal_move(turn):
    """check that illegal moves are added to error dict and bot still takes move"""
    game_state = setup_random_basic_gamestate()
    game_state["turn"] = turn
    team = turn % 2
    illegal_move = game_state["walls"][0]
    game_state_new = apply_move(game_state, illegal_move)
    assert len(game_state_new["errors"][team]) == 1
    assert set(game_state_new["errors"][team][0].keys()) == set(["turn", "round", "reason", "bot_position"])
    assert game_state_new["bots"][turn] in get_legal_moves(game_state["walls"], game_state["bots"][turn])

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
    game_state = setup_specific_basic_gamestate("layouts/small_without_dead_ends_001.layout")
    prev_len_food = len(game_state["food"])
    #turn = 0
    team = turn % 2
    game_state["turn"] = turn

    if which_food == 1:
        # food belongs to team 1
        game_state["bots"][turn] = (11, 1)
        move = (10, 1)
    else:
        # food belongs to team 0
        game_state["bots"][turn] = (6, 4)
        move = (7, 4)
    game_state_new = apply_move(game_state, move)

    if team == which_food:
        assert game_state_new["score"][team] == 0
        assert prev_len_food == len(game_state_new["food"])
    elif team != which_food:
        assert game_state_new["score"][team] > 0
        assert prev_len_food > len(game_state_new["food"])


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
    game_state = setup_specific_basic_gamestate("layouts/small_without_dead_ends_001.layout")
    team = turn % 2
    game_state["turn"] = turn
    enemy_idx = (1, 3) if team == 0 else(0, 2)
    (friend_idx,) = set([0, 1, 2, 3]) - set([*enemy_idx, turn])

    game_state_new = apply_move(game_state, game_state["bots"][friend_idx])
    # assert game_state_new["DEATHS"][team] == 5
    assert game_state_new["score"] == [0, 0]
    assert game_state_new["deaths"] == [0, 0]

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
    game_state = setup_specific_basic_gamestate("layouts/small_without_dead_ends_001.layout")
    turn = setups[0]
    enemy_pos = setups[1]
    team = turn % 2
    game_state["turn"] = turn
    enemy_idx = (1, 3) if team == 0 else (0, 2)
    game_state["bots"][enemy_idx[0]] = enemy_pos
    game_state_new = apply_move(game_state, enemy_pos)
    # assert game_state_new["DEATHS"][team] == 5
    assert game_state_new["score"][team] == 5



@pytest.mark.parametrize('score', ([[3, 3], 2], [[1, 13], 1], [[13, 1], 0]))
def test_play_turn_maxrounds(score):
    """Check that game quits at maxrounds and choses correct winner"""
    # this works for ties as well, because there are no points to be gained at init positions
    game_state = setup_random_basic_gamestate()
    game_state["round"] = 300
    game_state["score"] = score[0]
    move = get_legal_moves(game_state["walls"], game_state["bots"][0])
    game_state_new = apply_move(game_state, move[0])
    assert game_state_new["gameover"]
    assert game_state_new["whowins"] == score[1]

def test_play_turn_move():
    """Checks that bot is moved to intended space"""
    turn = 0
    l = Path("layouts/small_without_dead_ends_100.layout").read_text()
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
        "deaths": 0,
        "errors": [[], []],
        "fatal_errors": [{}, {}],
        "rnd": random.Random()
        }
    legal_moves = get_legal_moves(game_state["walls"], game_state["bots"][turn])
    game_state_new = apply_move(game_state, legal_moves[0])
    assert game_state_new["bots"][turn] == legal_moves[0]



def setup_random_basic_gamestate():
    """helper function for testing play turn"""
    turn = 0
    l = Path("layouts/small_without_dead_ends_100.layout").read_text()
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
        "score": [0, 0],
        "deaths": 0,
        "errors": [[], []],
        "fatal_errors": [{}, {}],
        "rnd": random.Random()
        }
    return game_state


def setup_specific_basic_gamestate(layout_id):
    """helper function for testing play turn"""
    turn = 0
    l = Path(layout_id).read_text()
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
        "score": [0, 0],
        "deaths": [0, 0],
        "errors": [[], []],
        "fatal_errors": [{}, {}],
        "rnd": random.Random()
        }
    return game_state


def test_minimal_game():
    def move(b, s):
        return b.position, s

    layout_name, layout_string = layout.get_random_layout()
    l = layout.parse_layout(layout_string)
    final_state = run_game([move, move], rounds=20, layout_dict=l)
    assert final_state['gameover'] is True
    assert final_state['score'] == [0, 0]
    assert final_state['round'] == 19

def test_minimal_losing_game_has_one_error():
    def move0(b, s):
        if b.round == 0 and b.bot_index == 0:
            # trigger a bad move in the first round
            return (0, 0), s
        else:
            return b.position, s
    def move1(b, s):
        return b.position, s

    layout_name, layout_string = layout.get_random_layout()
    l = layout.parse_layout(layout_string)
    final_state = run_game([move0, move1], rounds=20, layout_dict=l)
    assert final_state['gameover'] is True
    assert final_state['score'] == [0, 0]
    assert len(final_state['errors'][0]) == 1
    assert len(final_state['errors'][1]) == 0
    assert final_state['round'] == 19


def test_minimal_remote_game():
    def move(b, s):
        return b.position, s

    layout_name, layout_string = layout.get_random_layout()
    l = layout.parse_layout(layout_string)
    final_state = run_game(["test/demo01_stopping.py", move], rounds=20, layout_dict=l)
    final_state = run_game(["test/demo01_stopping.py", 'test/demo02_random.py'], rounds=20, layout_dict=l)
    assert final_state['gameover'] is True
    assert final_state['score'] == [0, 0]
    assert final_state['round'] == 19
