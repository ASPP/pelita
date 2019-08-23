import pytest

from pelita.layout import parse_layout, get_random_layout, initial_positions, layout_as_str
from pelita.game import run_game, setup_game, play_turn
from pelita.player.team import Team
from pelita.utils import setup_test_game

def stopping(bot, state):
    return bot.position, state

def randomBot(bot, state):
    legal = bot.legal_positions[:]
    return bot.random.choice(legal), state

layout1="""
########
# ###E0#
#1E    #
########
"""
layout2="""
########
# ###  #
# . ...#
########
"""


def test_load():
    layout = parse_layout(layout1+layout2, allow_enemy_chars=True)
    assert layout['bots'] == [(6, 1), (1, 2)]
    assert layout['enemy'] == [(2, 2), (5, 1)]

def test_load1():
    layout = parse_layout(layout1, allow_enemy_chars=True)
    assert layout['bots'] == [(6, 1), (1, 2)]
    assert layout['enemy'] == [(2, 2), (5, 1)]

def test_equal_positions():
    layout_str = """
        ########
        #0###  #
        # . ...#
        ########

        ########
        #1###  #
        # . ...#
        ########

        ########
        #E###  #
        # . ...#
        ########

        ########
        #E###  #
        # . ...#
        ########
    """
    layout = parse_layout(layout_str, allow_enemy_chars=True)
    assert layout['bots'] == [(1, 1), (1, 1)]
    assert layout['enemy'] ==  [(1, 1), (1, 1)]
    setup_test_game(layout=layout_str)

def test_define_after():
    layout = parse_layout(layout1, food=[(1, 1)], bots=[None, None], enemy=None, allow_enemy_chars=True)
    assert layout['bots'] == [(6, 1), (1, 2)]
    assert layout['enemy'] == [(2, 2), (5, 1)]
    layout = parse_layout(layout1, food=[(1, 1)], bots=[None, (1, 1)], enemy=None, allow_enemy_chars=True)
    assert layout['bots'] == [(6, 1), (1, 1)]
    assert layout['enemy'] == [(2, 2), (5, 1)]

    with pytest.raises(ValueError):
        # must define all enemies
        layout = parse_layout(layout1, food=[(1, 1)], bots=[None, (1, 2)], enemy=[(5, 1)], allow_enemy_chars=True)

    layout = parse_layout(layout2, food=[(1, 1)], bots=[None, (1, 2)], enemy=[(5, 1), (2, 2)], allow_enemy_chars=True)
    assert layout['bots'] == [None, (1, 2)]
    assert layout['enemy'] == [(5, 1), (2, 2)]

    with pytest.raises(ValueError):
        # placed bot on walls
        layout = parse_layout(layout2, food=[(1, 1)], bots=[(0, 1), (1, 2)], enemy=[(5, 1), (2, 2)], allow_enemy_chars=True)

    with pytest.raises(ValueError):
        # placed bot outside maze
        layout = parse_layout(layout2, food=[(1, 1)], bots=[(1, 40), (1, 2)], enemy=[(5, 1), (2, 2)], allow_enemy_chars=True)

    with pytest.raises(ValueError):
        # placed bot outside maze
        layout = parse_layout(layout2, food=[(1, 1)], bots=[(40, 40), (1, 2)], enemy=[(5, 1), (2, 2)], allow_enemy_chars=True)

    with pytest.raises(ValueError):
        # placed bot outside maze
        layout = parse_layout(layout2, food=[(1, 1)], bots=[(-40, 4), (1, 2)], enemy=[(5, 1), (2, 2)], allow_enemy_chars=True)

    with pytest.raises(ValueError):
        # too many bots
        layout = parse_layout(layout2, food=[(1, 1)], bots=[(1, 1), (1, 2), (2, 2)], enemy=[(5, 1), (2, 2)], allow_enemy_chars=True)

def test_repr():
    layout = parse_layout(layout1, food=[(1, 1)], bots=[None, None], enemy=None, allow_enemy_chars=True)
    str1 = layout_as_str(**layout)
    assert str1 == """\
########
#.###E0#
#1E    #
########
"""

    layout_merge = parse_layout(layout1, food=[(1, 1)], bots=[(1, 2), (1, 2)], enemy=[(1, 1), (1, 1)], allow_enemy_chars=True)
    str2 = layout_as_str(**layout_merge)
    assert str2 == """\
########
#.###  #
#      #
########
########
#E###  #
#0     #
########
########
#E###  #
#1     #
########
"""
    # load again
    assert parse_layout(str2, allow_enemy_chars=True) == layout_merge

def test_two_enemies():
    # single E evaluates to two enemies
    l = """
    ########
    #.###  #
    #      #
    ########

    ########
    # ###  #
    #0E    #
    ########
    """
    str1 = layout_as_str(**parse_layout(l, food=[(1, 1)], bots=[None, None], enemy=None, allow_enemy_chars=True))
    assert str1 == """\
########
#.###  #
#      #
########
########
# ###  #
#0E    #
########
########
# ###  #
# E    #
########
"""


class TestStoppingTeam:
    @staticmethod
    def round_counting():
        storage_copy = {}
        def inner(bot, state):
            print(state)
            if state is None:
                state = {}
            state[bot.turn] = state.get(bot.turn, 0) + 1
            storage_copy['rounds'] = state[bot.turn]
            print(state)
            return bot.position, state
        inner._storage = storage_copy
        return inner

    def test_stopping(self):
        test_layout = (
        """ ############
            #0#.23 .# 1#
            ############ """)

        round_counting = self.round_counting()
        team = [
            stopping,
            round_counting
        ]
        state = run_game(team, max_rounds=1, layout_dict=parse_layout(test_layout), allow_exceptions=True)
        assert state['bots'][0] == (1, 1)
        assert state['bots'][1] == (10, 1)
        assert round_counting._storage['rounds'] == 1

        round_counting = self.round_counting()
        team = [
            stopping,
            round_counting
        ]
        state = run_game(team, max_rounds=3, layout_dict=parse_layout(test_layout), allow_exceptions=True)
        assert state['bots'][0] == (1, 1)
        assert state['bots'][1] == (10, 1)
        assert round_counting._storage['rounds'] == 3

def test_track_and_kill_count():
    # for each team, we track whether they have been eaten at least once
    # and count the number of times they have been killed
    bot_states = {
        0: [{'track': [], 'eaten': False, 'times_killed': 0, 'deaths': 0},
            {'track': [], 'eaten': False, 'times_killed': 0, 'deaths': 0}],
        1: [{'track': [], 'eaten': False, 'times_killed': 0, 'deaths': 0},
            {'track': [], 'eaten': False, 'times_killed': 0, 'deaths': 0}]
    }
    def trackingBot(bot, state):
        turn = bot.turn
        other = bot.other

        # first move. get the state from the global cache
        if state is None:
            team_idx = 0 if bot.is_blue else 1
            state = bot_states[team_idx]

        if bot.round == 1 and turn == 0:
            assert bot.track[0] == bot.position

        if bot.was_killed:
            state[turn]['eaten'] = True
            # if bot.deaths has increased from our last known value,
            # we add a kill
            # this avoids adding two kills as the eaten attribute could
            # be True in two consecutive turns
            if state[turn]['deaths'] != bot.deaths:
                state[turn]['times_killed'] += 1
            state[turn]['deaths'] = bot.deaths
        if other.was_killed:
            state[1 - turn]['eaten'] = True
            if state[1 - turn]['deaths'] != bot.other.deaths:
                state[1 - turn]['times_killed'] += 1
            state[1 - turn]['deaths'] = bot.other.deaths

        if bot.was_killed or not state[turn]['track']:
            state[turn]['track'] = [bot.position]
        if other.was_killed or not state[1 - turn]['track']:
            state[1 - turn]['track'] = [other.position]
        else:
            state[1 - turn]['track'].append(other.position)

        # The assertion is that the first position in bot.track
        # is always the respawn position.
        # However, in our test case, this will only happen, once
        # a bot has been eaten.
        if state[turn]['eaten']:
            assert bot.track[0] == bot._initial_position
        assert bot.track == state[turn]['track'] # bot.round * 2 + 1 + turn
        assert bot.track[-1] == bot.position
        # just move randomly. hopefully, this means some bots will be killed
        return randomBot(bot, state)

    layout = """
    ##########
    # 02 .3 1#
    # ########
    #.##. .###
    ##########
    """
    team = [
        trackingBot,
        trackingBot
    ]
    state = setup_game(team, max_rounds=300, layout_dict=parse_layout(layout))
    while not state['gameover']:
        # Check that our count is consistent with what the game thinks
        # for the current and previous bot, we have to subtract the deaths that have just respawned
        # as they have not been passed to the bot yet
        # therefore, we only update old_deaths for the current team

        if state['turn'] is not None:
            old_deaths[state['turn']] = state['deaths'][state['turn']]

        old_deaths = state['deaths'][:]
        state = play_turn(state)
        deaths = state['deaths'][:]

        team = state['turn'] % 2

        # The current bot knows about its deaths, *unless* it made suicide,
        # so we have to subtract 1 if bot_was_killed is True
        suicide_correction = [0] * 4
        suicide_correction[state['turn']] = 1 if state['bot_was_killed'][state['turn']] else 0

        # The other team knows about its deaths, *unless* one of the bots got eaten
        # just now, or the previous bot made suicide
        other_team_correction = [0] * 4
        for idx in range(1 - team, 4, 2):
            if old_deaths[idx] != deaths[idx]:
                other_team_correction[idx] = 1

        # suicide
        prev_idx = state['turn'] - 1
        if old_deaths[prev_idx] == deaths[prev_idx] and state['bot_was_killed'][prev_idx]:
            other_team_correction[prev_idx] = 1

        assert bot_states[0][0]['times_killed'] == deaths[0] - suicide_correction[0] - other_team_correction[0]
        assert bot_states[1][0]['times_killed'] == deaths[1] - suicide_correction[1] - other_team_correction[1]
        assert bot_states[0][1]['times_killed'] == deaths[2] - suicide_correction[2] - other_team_correction[2]
        assert bot_states[1][1]['times_killed'] == deaths[3] - suicide_correction[3] - other_team_correction[3]

        # assertions might have been caught in run_game
        # check that all is good
        assert state['fatal_errors'] == [[], []]

    # check that the game has run at all
    assert state['round'] >= 1
    # check that someone has been killed, or the whole test is not doing anything
    assert sum(state['deaths']) > 0
    # check that each single bot has been eaten, or we are not testing the full range of possibilities
    assert all(state['deaths'])


@pytest.mark.parametrize('bot_to_move', range(4))
def test_eaten_flag_kill(bot_to_move):
    """ Test that the eaten flag is set correctly in kill situations. """
    layout = """
    ########
    #  10  #
    #  32  #
    #......#
    ########
    """
    def move(bot, state):
        x, y = bot.position
        new_pos = bot.position
        if bot_to_move == 0:
            # we move in the first round as blue team in turn == 0
            if bot.round == 1 and bot.is_blue and bot.turn == 0:
                new_pos = (x - 1, y)
            # The red team should notice immediately
            if bot.round == 1 and not bot.is_blue and bot.turn == 0:
                assert bot.was_killed
                assert bot.other.was_killed is False
            # as bot 1 has been moved, the eaten flag will be reset in all other cases
            else:
                assert bot.was_killed is False
                assert bot.other.was_killed is False
        if bot_to_move == 1:
            # we move in the first round as red team
            if bot.round == 1 and not bot.is_blue and bot.turn == 0:
                new_pos = (x + 1, y)
            # The other team should notice immediately that its other bot (#0) has been eaten
            if bot.round == 1 and bot.is_blue and bot.turn == 1:
                assert bot.was_killed is False
                assert bot.other.was_killed
            # When bot 0 moves, the flag is still set
            elif bot.round == 2 and bot.is_blue and bot.turn == 0:
                assert bot.was_killed
                assert bot.other.was_killed is False
            else:
                assert bot.was_killed is False
                assert bot.other.was_killed is False
        if bot_to_move == 2:
            # we move in the first round as blue team in turn == 1
            if bot.round == 1 and bot.is_blue and bot.turn == 1:
                new_pos = (x - 1, y)
            # The red team should notice immediately
            if bot.round == 1 and not bot.is_blue and bot.turn == 1:
                assert bot.was_killed
                assert bot.other.was_killed is False
            # as bot 2 has been moved, the eaten flag will be reset in all other cases
            else:
                assert bot.was_killed is False
                assert bot.other.was_killed is False
        if bot_to_move == 3:
            # we move in the first round as red team in turn == 1
            if bot.round == 1 and not bot.is_blue and bot.turn == 1:
                new_pos = (x + 1, y)
            # The blue team should notice immediately (in round == 2!) that bot 1 has been eaten
            if bot.round == 2 and bot.is_blue and bot.turn == 0:
                assert bot.was_killed is False
                assert bot.other.was_killed
            # When bot 1 moves, the flag is still set
            elif bot.round == 2 and bot.is_blue and bot.turn == 1:
                assert bot.was_killed
                assert bot.other.was_killed is False
            else:
                assert bot.was_killed is False
                assert bot.other.was_killed is False

        # otherwise return current position
        return new_pos, state
    state = run_game([move, move], max_rounds=3, layout_dict=parse_layout(layout), allow_exceptions=True)
    # assertions might have been caught in run_game
    # check that all is good
    assert state['fatal_errors'] == [[], []]


@pytest.mark.parametrize("bot_to_move", range(4))
def test_eaten_flag_suicide(bot_to_move):
    """ Test that the eaten flag is set correctly in suicide situations. """
    layout = """
    ########
    #  01  #
    #  23  #
    #......#
    ########
    """
    def move(bot, state):
        x, y = bot.position
        new_pos = bot.position
        if bot_to_move == 0:
            # we move in the first round as blue team in turn == 0
            if bot.round == 1 and bot.is_blue and bot.turn == 0:
                new_pos = (x + 1, y)
            # our other bot should notice it in our next turn
            if bot.round == 1 and bot.is_blue and bot.turn == 1:
                assert bot.was_killed is False
                assert bot.other.was_killed
            # bot 0 will notice it in the next round
            elif bot.round == 2 and bot.is_blue and bot.turn == 0:
                assert bot.was_killed
                assert bot.other.was_killed is False
            else:
                assert bot.was_killed is False
                assert bot.other.was_killed is False
        if bot_to_move == 1:
            # we move in the first round as red team
            if bot.round == 1 and not bot.is_blue and bot.turn == 0:
                new_pos = (x - 1, y)
            # we should notice in our next turn
            if bot.round == 1 and not bot.is_blue and bot.turn == 1:
                assert bot.was_killed is False
                assert bot.other.was_killed
            # bot 1 will notice it in the next round
            elif bot.round == 2 and not bot.is_blue and bot.turn == 0:
                assert bot.was_killed
                assert bot.other.was_killed is False
            else:
                assert bot.was_killed is False
                assert bot.other.was_killed is False
        if bot_to_move == 2:
            # we move in the first round as blue team in turn == 1
            if bot.round == 1 and bot.is_blue and bot.turn == 1:
                new_pos = (x + 1, y)
            # we should notice in our next turn (next round!)
            if bot.round == 2 and bot.is_blue and bot.turn == 0:
                assert bot.was_killed is False
                assert bot.other.was_killed
            # bot 2 will notice it in the next round as well
            elif bot.round == 2 and bot.is_blue and bot.turn == 1:
                assert bot.was_killed
                assert bot.other.was_killed is False
            else:
                assert bot.was_killed is False
                assert bot.other.was_killed is False
        if bot_to_move == 3:
            # we move in the first round as red team in turn == 1
            if bot.round == 1 and not bot.is_blue and bot.turn == 1:
                new_pos = (x - 1, y)
            # we should notice in our next turn (next round!)
            if bot.round == 2 and not bot.is_blue and bot.turn == 0:
                assert bot.was_killed is False
                assert bot.other.was_killed
            # bot 3 will notice it in the next round as well
            elif bot.round == 2 and not bot.is_blue and bot.turn == 1:
                assert bot.was_killed
                assert bot.other.was_killed is False
            else:
                assert bot.was_killed is False
                assert bot.other.was_killed is False

        # otherwise return current position
        return new_pos, state
    state = run_game([move, move], max_rounds=3, layout_dict=parse_layout(layout), allow_exceptions=True)
    # assertions might have been caught in run_game
    # check that all is good
    assert state['fatal_errors'] == [[], []]


@pytest.mark.parametrize('_n_test', range(10))
def test_initial_position(_n_test):
    """ Test that out test team receives the correct initial positions."""
    layout_name, layout_string = get_random_layout()
    l = parse_layout(layout_string)
    initial_pos = initial_positions(l['walls'])

    def move(bot, state):
        if bot.is_blue and bot.turn == 0:
            assert bot._initial_position == initial_pos[0]
            assert bot.other._initial_position == initial_pos[2]
            assert bot.enemy[0]._initial_position == initial_pos[1]
            assert bot.enemy[1]._initial_position == initial_pos[3]
        if bot.is_blue and bot.turn == 1:
            assert bot._initial_position == initial_pos[2]
            assert bot.other._initial_position == initial_pos[0]
            assert bot.enemy[0]._initial_position == initial_pos[1]
            assert bot.enemy[1]._initial_position == initial_pos[3]
        if not bot.is_blue and bot.turn == 0:
            assert bot._initial_position == initial_pos[1]
            assert bot.other._initial_position == initial_pos[3]
            assert bot.enemy[0]._initial_position == initial_pos[0]
            assert bot.enemy[1]._initial_position == initial_pos[2]
        if not bot.is_blue and bot.turn == 1:
            assert bot._initial_position == initial_pos[3]
            assert bot.other._initial_position == initial_pos[1]
            assert bot.enemy[0]._initial_position == initial_pos[0]
            assert bot.enemy[1]._initial_position == initial_pos[2]
        return randomBot(bot, state)

    state = run_game([move, move], max_rounds=3, layout_dict=l)
    # assertions might have been caught in run_game
    # check that all is good
    assert state['fatal_errors'] == [[], []]


def test_bot_attributes():
    test_layout = """
        ##################
        #.#... .##.     3#
        # # #  .  .### #1#
        # ####.   .      #
        #      .   .#### #
        #0# ###.  .  # # #
        #2     .##. ...#.#
        ##################
    """

    parsed = parse_layout(test_layout)
    width = max(parsed['walls'])[0] + 1
    height = max(parsed['walls'])[1] + 1
    homezones = [[], []]
    homezones[0] = [(x, y)
                    for x in range(0, width // 2)
                    for y in range(0, height)]
    homezones[1] = [(x, y)
                    for x in range(width // 2, width)
                    for y in range(0, height)]

    assert set(homezones[0]) & set(homezones[1]) == set()

    def asserting_team(bot, state):
        assert bot.homezone == bot.other.homezone
        assert bot.walls == parsed['walls']
        if bot.is_blue:
            assert set(bot.homezone) == set(homezones[0])
            assert set(bot.enemy[0].homezone) == set(homezones[1])
        else:
            assert set(bot.homezone) == set(homezones[1])
            assert set(bot.enemy[0].homezone) == set(homezones[0])
        return bot.position, state

    state = run_game([asserting_team, asserting_team], max_rounds=1, layout_dict=parsed)
    # assertions might have been caught in run_game
    # check that all is good
    assert state['fatal_errors'] == [[], []]

