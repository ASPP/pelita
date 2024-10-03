import time

import pytest
import networkx

from pelita.layout import parse_layout, get_random_layout, initial_positions
from pelita.game import run_game, setup_game, play_turn, SHADOW_DISTANCE
from pelita.gamestate_filters import manhattan_dist

def stopping(bot, state):
    return bot.position

def randomBot(bot, state):
    legal = bot.legal_positions[:]
    return bot.random.choice(legal)

class TestStoppingTeam:
    @staticmethod
    def round_counting():
        storage_copy = {}
        def inner(bot, state):
            print(state)
            state[bot.turn] = state.get(bot.turn, 0) + 1
            storage_copy['rounds'] = state[bot.turn]
            print(state)
            return bot.position
        inner._storage = storage_copy
        return inner

    def test_stopping(self):
        test_layout = (
        """ ############
            #a#.by .# x#
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
        if state == {}:
            team_idx = 0 if bot.is_blue else 1
            state.update(enumerate(bot_states[team_idx]))

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
    # ab .y x#
    # ########
    #.##. .###
    ##########
    """
    team = [
        trackingBot,
        trackingBot
    ]
    # We play 600 rounds as we rely on some randomness in our assertions
    state = setup_game(team, max_rounds=600, allow_camping=True, layout_dict=parse_layout(layout))
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
    #  xa  #
    #  yb  #
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
        return new_pos
    state = run_game([move, move], max_rounds=3, layout_dict=parse_layout(layout), allow_exceptions=True)
    # assertions might have been caught in run_game
    # check that all is good
    assert state['fatal_errors'] == [[], []]


@pytest.mark.parametrize("bot_to_move", range(4))
def test_eaten_flag_suicide(bot_to_move):
    """ Test that the eaten flag is set correctly in suicide situations. """
    layout = """
    ########
    #  ax  #
    #  by  #
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
        return new_pos
    state = run_game([move, move], max_rounds=3, layout_dict=parse_layout(layout), allow_exceptions=True)
    # assertions might have been caught in run_game
    # check that all is good
    assert state['fatal_errors'] == [[], []]


@pytest.mark.parametrize('_n_test', range(10))
def test_initial_position(_n_test):
    """ Test that out test team receives the correct initial positions."""
    layout_name, layout_string = get_random_layout()
    l = parse_layout(layout_string)
    initial_pos = initial_positions(l['walls'], l['shape'])

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
        #.#... .##.     y#
        # #a#  .  .### #x#
        # ####.   .      #
        #      .   .#### #
        # # ###.  .  # # #
        #b     .##. ...#.#
        ##################
    """

    parsed = parse_layout(test_layout)
    width = max(parsed['walls'])[0] + 1
    height = max(parsed['walls'])[1] + 1
    homezones = [[], []]
    homezones[0] = [(x, y)
                    for x in range(0, width // 2)
                    for y in range(0, height)
                    if (x, y) not in parsed['walls']]
    homezones[1] = [(x, y)
                    for x in range(width // 2, width)
                    for y in range(0, height)
                    if (x, y) not in parsed['walls']]

    assert set(homezones[0]) & set(homezones[1]) == set()

    def asserting_team(bot, state):
        assert bot.homezone == bot.other.homezone
        assert bot.walls == parsed['walls']

        assert bot.walls == tuple(sorted(bot.walls))
        assert bot.homezone == tuple(sorted(bot.homezone))
        if bot.is_blue:
            assert set(bot.homezone) == set(homezones[0])
            assert set(bot.enemy[0].homezone) == set(homezones[1])
            shaded_food = set(food for food in bot.food if
                              manhattan_dist(bot.position, food) <= SHADOW_DISTANCE or
                              manhattan_dist(bot.other.position, food) <= SHADOW_DISTANCE)
            assert set(bot.shaded_food) == shaded_food
            assert set(bot.other.shaded_food) == shaded_food
            assert set(bot.enemy[0].shaded_food) == set()
            assert set(bot.enemy[1].shaded_food) == set()
        else:
            assert set(bot.homezone) == set(homezones[1])
            assert set(bot.enemy[0].homezone) == set(homezones[0])
            assert set(bot.shaded_food) == set()
            assert set(bot.other.shaded_food) == set()
            assert set(bot.enemy[0].shaded_food) == set()
            assert set(bot.enemy[1].shaded_food) == set()
        return bot.position

    state = run_game([asserting_team, asserting_team], max_rounds=1, layout_dict=parsed)
    # assertions might have been caught in run_game
    # check that all is good
    assert state['errors'] == [{}, {}]
    assert state['fatal_errors'] == [[], []]

def test_bot_graph():
    layout = """
    ########
    #  ax  #
    #  by  #
    #......#
    ########
    """
    def rough_bot(bot, state):
        # check that we have this node in the graph at the beginning
        assert (1, 1) in bot.graph
        # check that we can't remove a node
        with pytest.raises(networkx.NetworkXError):
            bot.graph.remove_node((1, 1))
        # check that we can't add a node
        with pytest.raises(networkx.NetworkXError):
            bot.graph.add_node((100, 100))
        # check that I can create my own copy of the graph and that this copy is
        # writable
        my_graph = bot.graph.copy()
        my_graph.remove_node((1, 1))
        assert (1, 1) not in my_graph
        return bot.position

    state  = run_game([rough_bot, stopping], max_rounds=1, layout_dict=parse_layout(layout))
    # assertions might have been caught in run_game
    # check that all is good
    assert state['errors'] == [{}, {}]
    assert state['fatal_errors'] == [[], []]

def test_bot_graph_is_half_mutable():
    # Test that a bot can change the weights of the graph
    # Changing the weights affects the future self of the bot
    # Changing the weights does affect the other bot in the team
    # Changing the weights does not affect the other team
    layout = """
    ########
    #  ax  #
    #  by  #
    #......#
    ########
    """

    observer = []

    def blue(bot, state):
        if bot.turn == 0 and bot.round == 1:
            assert bot.graph[1, 1][1, 2].get('weight') is None
            bot.graph[1, 1][1, 2]['weight'] = 1
            observer.append('B')
        else:
            assert bot.graph[1, 1][1, 2].get('weight') == 1
            observer.append('b')

        return bot.position

    def red(bot, state):
        if bot.turn == 0 and bot.round == 1:
            assert bot.graph[1, 1][1, 2].get('weight') is None
            bot.graph[1, 1][1, 2]['weight'] = 2
            observer.append('R')
        else:
            assert bot.graph[1, 1][1, 2].get('weight') == 2
            observer.append('r')

        return bot.position

    state  = run_game([blue, red], max_rounds=2, layout_dict=parse_layout(layout))
    # assertions might have been caught in run_game
    # check that all is good
    assert state['errors'] == [{}, {}]
    assert state['fatal_errors'] == [[], []]
    assert "".join(observer) == 'BRbrbrbr'


def test_team_names():
    test_layout = (
    """ ##################
        #a#.  .  # .     #
        #b#####    #####x#
        #     . #  .  .#y#
        ################## """)

    def team_pattern(fn):
        # The pattern for a local team.
        return f'local-team ({fn})'

    def team_1(bot, state):
        assert bot.team_name == team_pattern('team_1')
        assert bot.other.team_name == team_pattern('team_1')
        assert bot.enemy[0].team_name == team_pattern('team_2')
        assert bot.enemy[1].team_name == team_pattern('team_2')
        return bot.position

    def team_2(bot, state):
        assert bot.team_name == team_pattern('team_2')
        assert bot.other.team_name == team_pattern('team_2')
        assert bot.enemy[0].team_name == team_pattern('team_1')
        assert bot.enemy[1].team_name == team_pattern('team_1')
        return bot.position

    state = setup_game([team_1, team_2], layout_dict=parse_layout(test_layout), max_rounds=3)
    assert state['team_names'] == [team_pattern('team_1'), team_pattern('team_2')]

    state = play_turn(state)
    # check that player did not fail
    assert state['errors'] == [{}, {}]
    assert state['fatal_errors'] == [[], []]

    state = play_turn(state)
    # check that player did not fail
    assert state['errors'] == [{}, {}]
    assert state['fatal_errors'] == [[], []]


def test_team_time():
    test_layout = (
    """ ##################
        #a#.  .  # .     #
        #b#####    #####x#
        #     . #  .  .#y#
        ################## """)

    def team_pattern(fn):
        # The pattern for a local team.
        return f'local-team ({fn})'

    # NB: time.monotonic() makes huge leaps on windows,
    # we must therefore test with >= instead of just >
    # although this is a little stupid

    check = [None, None]

    def team_1(bot, state):
        if bot.round == 1 and bot.turn == 0:
            assert bot.team_time == 0
            assert bot.enemy[0].team_time == 0
        else:
            assert bot.team_time >= 0

        # we fake the time in round 2!!
        if bot.round == 2 and bot.turn == 0:
            assert bot.team_time == 1.0
            assert bot.enemy[0].team_time == 2.0

        if bot.round == 2 and bot.turn == 1:
            assert bot.team_time >= 1.0
            assert bot.enemy[0].team_time >= 2.0

        check[0] = bot.team_time

        return bot.position

    def team_2(bot, state):
        if bot.round == 1 and bot.turn == 0:
            assert bot.team_time == 0
            assert bot.enemy[0].team_time >= 0
        else:
            assert bot.team_time >= 0

        # we fake the time in round 2!!
        if bot.round == 2 and bot.turn == 0:
            assert bot.team_time == 2.0
            assert bot.enemy[0].team_time >= 1.0

        if bot.round == 2 and bot.turn == 1:
            assert bot.team_time >= 2.0
            assert bot.enemy[0].team_time >= 1.0

        check[1] = bot.team_time

        return bot.position

    state = setup_game([team_1, team_2], layout_dict=parse_layout(test_layout), max_rounds=3, allow_exceptions=True)

    state = play_turn(state)
    assert state['team_time'][0] >= 0
    assert state['team_time'][1] == 0

    state = play_turn(state)
    assert state['team_time'][0] >= 0
    assert state['team_time'][1] >= 0

    # time before bots get updated
    old_time = list(state['team_time'])

    state = play_turn(state)
    state = play_turn(state)

    assert check == old_time

    # Round 2. We fake the time so we do not have to sleep!
    state['team_time'] = [1.0, 2.0]

    state = play_turn(state)
    state = play_turn(state)

    # time before bots get updated
    old_time = list(state['team_time'])

    state = play_turn(state)
    state = play_turn(state)

    assert check == old_time

    # check that player did not fail
    assert state['errors'] == [{}, {}]
    assert state['fatal_errors'] == [[], []]
    assert state['team_time'][0] >= 1.0
    assert state['team_time'][1] >= 2.0


def test_bot_str_repr():
    test_layout = """
        ##################
        #.#... .##.     y#
        # # #  .  .### #x#
        # ####.   .      #
        #      .   .#### #
        #a# ###.  .  # # #
        #b     .##. ...#.#
        ##################
    """

    parsed = parse_layout(test_layout)

    def asserting_team(bot, state):
        bot_str = str(bot).split('\n')
        if bot.is_blue and bot.round == 1:
            assert bot_str[0] == "local-team (asserting_team) (you) vs local-team (asserting_team)."
            assert bot_str[1] == f"Playing on blue side. Current turn: {bot.turn}. Bot: {bot.char}. Round: 1, score: 0:0. timeouts: 0:0"
        elif not bot.is_blue and bot.round == 1:
            assert bot_str[0] == "local-team (asserting_team) vs local-team (asserting_team) (you)."
            assert bot_str[1] == f"Playing on red side. Current turn: {bot.turn}. Bot: {bot.char}. Round: 1, score: 0:0. timeouts: 0:0"
        else:
            assert False, "Should never be here."

        return bot.position

    state = run_game([asserting_team, asserting_team], max_rounds=1, layout_dict=parsed,
                     allow_exceptions=True)
    # assertions might have been caught in run_game
    # check that all is good
    assert state['fatal_errors'] == [[], []]


def test_bot_html_repr():
    test_layout = """
        ##################
        #.#... .##.     y#
        # # #  .  .### #x#
        # ####.   .      #
        #      .   .#### #
        #a# ###.  .  # # #
        #b     .##. ...#.#
        ##################
    """

    parsed = parse_layout(test_layout)

    def asserting_team(bot, state):
        # Not a full-fledged test at this time. We mainly want to catch API changes for now.

        bot_str = bot._repr_html_()
        assert len(bot_str)

        return bot.position

    state = run_game([asserting_team, asserting_team], max_rounds=1, layout_dict=parsed,
                     allow_exceptions=True)
    # assertions might have been caught in run_game
    # check that all is good
    assert state['fatal_errors'] == [[], []]

