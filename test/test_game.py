"""Tests for Pelita game module"""
import pytest
import numpy as np
from pelita.game import initial_positions
from pelita.game import play_turn
from pelita.game import get_legal_moves

from pelita import layout

def test_initial_positions_basic():
    """Checks basic example for initial positions"""
    walls = [(0, 0),
             (0, 1),
             (0, 2),
             (0, 3),
             (1, 0),
             (1, 3),
             (2, 0),
             (2, 1),
             (2, 3),
             (3, 0),
             (3, 1),
             (3, 3),
             (4, 0),
             (4, 1),
             (4, 3),
             (5, 0),
             (5, 3),
             (6, 0),
             (6, 3),
             (7, 0),
             (7, 1),
             (7, 2),
             (7, 3)]
    out = initial_positions(walls)
    exp = [(1, 1), (6, 2), (1, 2), (6, 1)]
    assert len(out) == 4
    assert out == exp

@pytest.mark.parametrize('n_times', range(30))
def test_initial_positions_same_in_layout_random(n_times):
    """Check initial positions are the same as what the layout says for 30 random layouts"""
    seedval = np.random.randint(2**32)
    print(f'seedval: {seedval}')
    l = layout.get_random_layout()
    parsed_l = layout.parse_layout(l[1])
    exp = parsed_l["bots"]
    walls = parsed_l["walls"]
    out = initial_positions(walls)
    assert out == exp

@pytest.mark.parametrize('layout_name', layout.get_available_layouts())
def test_initial_positions_same_in_layout(layout_name):
    """Check initial positions are the same as what the layout says for all layouts"""
    l = layout.load_layout(layout_name=layout_name)
    parsed_l = layout.parse_layout(l[1])
    exp = parsed_l["bots"]
    walls = parsed_l["walls"]
    out = initial_positions(walls)
    assert out == exp

def test_get_legal_moves_basic():
    """Check that the output of legal moves contains all legal moves for one example layout"""
    l = layout.load_layout(layout_name="layout_small_without_dead_ends_100")
    # l = layout.load_layout(layout_name="layout_normal_with_dead_ends_100")
    parsed_l = layout.parse_layout(l[1])
    legal_moves = get_legal_moves(parsed_l["walls"], parsed_l["bots"][0])
    exp = [(2, 5), (1, 6), (1, 5)]
    assert legal_moves == exp

@pytest.mark.parametrize('n_times', range(50))
@pytest.mark.parametrize('bot_idx', (0, 1, 2, 3))
def test_get_legal_moves_random(n_times, bot_idx):
    """Check that the output of legal moves returns only moves that are 1 field away and not inside a wall"""
    seedval = np.random.randint(2**32)
    print(f'seedval: {seedval}')
    l = layout.get_random_layout()
    parsed_l = layout.parse_layout(l[1])
    bot = parsed_l["bots"][bot_idx]
    legal_moves = get_legal_moves(parsed_l["walls"], bot)
    for move in legal_moves:
        assert move not in parsed_l["walls"]
        assert  abs((move[0] - bot[0])+(move[1] - bot[1])) <= 1


@pytest.mark.parametrize('turn', (0, 1, 2, 3))
def test_play_turn_apply_error(turn):
    """check that quits when there are too many errors"""
    seedval = np.random.randint(2**32)
    print(f'seedval: {seedval}')
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
    game_state_new = play_turn(game_state, illegal_move)
    assert game_state_new["gameover"]
    assert len(game_state_new["errors"][team]) == 5
    assert game_state_new["whowins"] == int(not team)
    assert set(game_state_new["errors"][team][4].keys()) == set(["turn", "round", "reason", "bot_position"])

@pytest.mark.parametrize('turn', (0, 1, 2, 3))
def test_play_turn_fatal(turn):
    """Checks that game quite after fatal error"""
    seedval = np.random.randint(2**32)
    print(f'seedval: {seedval}')
    game_state = setup_random_basic_gamestate()
    game_state["turn"] = turn
    team = turn % 2
    fatal_list = [{}, {}]
    fatal_list[team] = {"error":True}
    game_state["fatal_errors"] = fatal_list
    move = get_legal_moves(game_state["walls"], game_state["bots"][turn])
    game_state_new = play_turn(game_state, move[0])
    assert game_state_new["gameover"]
    assert game_state_new["whowins"] == int(not team)

@pytest.mark.parametrize('turn', (0, 1, 2, 3))
def test_play_turn_illegal_move(turn):
    """check that illegal moves are added to error dict and bot still takes move"""
    seedval = np.random.randint(2**32)
    print(f'seedval: {seedval}')
    game_state = setup_random_basic_gamestate()
    game_state["turn"] = turn
    team = turn % 2
    illegal_move = game_state["walls"][0]
    game_state_new = play_turn(game_state, illegal_move)
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
    game_state_new = play_turn(game_state, move)

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

    game_state_new = play_turn(game_state, game_state["bots"][friend_idx])
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
    game_state_new = play_turn(game_state, enemy_pos)
    # assert game_state_new["DEATHS"][team] == 5
    assert game_state_new["score"][team] == 5



@pytest.mark.parametrize('score', ([[3, 3], 2], [[1, 13], 1], [[13, 1], 0]))
def test_play_turn_maxrounds(score):
    """Check that game quits at maxrounds and choses correct winner"""
    # this works for ties as well, because there are no points to be gained at init positions
    seedval = np.random.randint(2**32)
    print(f'seedval: {seedval}')
    game_state = setup_random_basic_gamestate()
    game_state["round"] = 300
    game_state["score"] = score[0]
    move = get_legal_moves(game_state["walls"], game_state["bots"][0])
    game_state_new = play_turn(game_state, move[0])
    assert game_state_new["gameover"]
    assert game_state_new["whowins"] == score[1]

def test_play_turn_move():
    """Checks that bot is moved to intended space"""
    seedval = np.random.randint(2**32)
    print(f'seedval: {seedval}')
    turn = 0
    l = layout.load_layout(layout_file="layouts/small_without_dead_ends_100.layout")
    parsed_l = layout.parse_layout(l[1])
    game_state = {
        "food": parsed_l["food"],
        "walls": parsed_l["walls"],
        "bots": parsed_l["bots"],
        "max_round": 300,
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
        }
    legal_moves = get_legal_moves(game_state["walls"], game_state["bots"][turn])
    print(legal_moves)
    game_state_new = play_turn(game_state, legal_moves[0])
    assert game_state_new["bots"][turn] == legal_moves[0]


@pytest.mark.xfail()
def test_minimal_game():
    def move(b, s):
        return b.position, s

    layout_name, layout_string = layout.get_random_layout()
    l = layout.parse_layout(layout_string)
    run_game([move, move], rounds=20, layout_dict=l)

def setup_random_basic_gamestate():
    """helper function for testing play turn"""
    turn = 0
    l = layout.load_layout(layout_file="layouts/small_without_dead_ends_100.layout")
    parsed_l = layout.parse_layout(l[1])
    game_state = {
        "food": parsed_l["food"],
        "walls": parsed_l["walls"],
        "bots": parsed_l["bots"],
        "max_round": 300,
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
        }
    return game_state


def setup_specific_basic_gamestate(layout_id):
    """helper function for testing play turn"""
    turn = 0
    l = layout.load_layout(layout_file=layout_id)
    parsed_l = layout.parse_layout(l[1])
    game_state = {
        "food": parsed_l["food"],
        "walls": parsed_l["walls"],
        "bots": parsed_l["bots"],
        "max_round": 300,
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
        }
    return game_state
