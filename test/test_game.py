"""Tests for Pelita game module"""
import pytest

from pathlib import Path
import random

import numpy as np

from pelita import game, layout
from pelita.game import initial_positions, get_legal_moves, apply_move, run_game, setup_game

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
    game_state = setup_specific_basic_gamestate("layouts/small_without_dead_ends_001.layout", round=0, turn=turn)
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


@pytest.mark.parametrize('score', ([[3, 3], 2], [[1, 13], 1], [[13, 1], 0]))
def test_play_turn_maxrounds(score):
    """Check that game quits at maxrounds and choses correct winner"""
    # this works for ties as well, because there are no points to be gained at init positions
    game_state = setup_random_basic_gamestate()
    game_state["round"] = 300
    game_state["score"] = score[0]
    game_state_new = game.play_turn(game_state)
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



def setup_random_basic_gamestate(*, round=0, turn=0):
    """helper function for testing play turn"""
    turn = 0
    l = Path("layouts/small_without_dead_ends_100.layout").read_text()
    parsed_l = layout.parse_layout(l)

    stopping = lambda bot, s: (bot.position, s)

    game_state = setup_game([stopping, stopping], layout_dict=parsed_l)
    game_state['round'] = round
    game_state['turn'] = turn
    return game_state


def setup_specific_basic_gamestate(layout_id, *, round=0, turn=0):
    """helper function for testing play turn"""
    l = Path(layout_id).read_text()
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
        # in the first round (round #0),
        # all bots move to the south
        if bot.round == 0:
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
    # max_rounds == 0 should not call move at all
    final_state = run_game([move, move], layout_dict=l, max_rounds=0)
    assert final_state['round'] is None
    assert final_state['bots'][0] == (2, 1)
    assert final_state['bots'][1] == (5, 1)
    assert final_state['bots'][2] == (1, 1)
    assert final_state['bots'][3] == (6, 1)
    # max_rounds == 1 should call move just once
    final_state = run_game([move, move], layout_dict=l, max_rounds=1)
    assert final_state['round'] == 0
    assert final_state['bots'][0] == (2, 2)
    assert final_state['bots'][1] == (5, 2)
    assert final_state['bots'][2] == (1, 2)
    assert final_state['bots'][3] == (6, 2)
    with pytest.raises(RuntimeError):
        final_state = run_game([move, move], layout_dict=l, max_rounds=2)


def test_update_round_counter():
    tests = {
        (None, None): (0, 0),
        (0, 0): (0, 1),
        (0, 1): (0, 2),
        (0, 2): (0, 3),
        (0, 3): (1, 0),
        (1, 3): (2, 0)
    }

    for (round0, turn0), (round1, turn1) in tests.items():
        res = game.update_round_counter({'turn': turn0, 'round': round0, 'gameover': False})
        assert res == {'turn': turn1, 'round': round1}
    pass


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
        if team_to_move == 0 and bot.is_blue and bot_turn == bot.bot_turn:
            return (4, 1), s
            # eat the food between 0 and 2
        if team_to_move == 1 and (not bot.is_blue) and bot_turn == bot.bot_turn:
            # eat the food between 3 and 1
            return (3, 2), s
        return bot.position, s

    l = layout.parse_layout(l)
    final_state = run_game([move, move], layout_dict=l, max_rounds=20)
    assert final_state['round'] == 0
    assert final_state['turn'] == bot_to_move



def test_minimal_game():
    def move(b, s):
        return b.position, s

    layout_name, layout_string = layout.get_random_layout()
    l = layout.parse_layout(layout_string)
    final_state = run_game([move, move], max_rounds=20, layout_dict=l)
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
    final_state = run_game([move0, move1], max_rounds=20, layout_dict=l)
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
    final_state = run_game(["test/demo01_stopping.py", move], max_rounds=20, layout_dict=l)
    final_state = run_game(["test/demo01_stopping.py", 'test/demo02_random.py'], max_rounds=20, layout_dict=l)
    assert final_state['gameover'] is True
    assert final_state['score'] == [0, 0]
    assert final_state['round'] == 19
