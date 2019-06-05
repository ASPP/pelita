import pytest

from pelita.layout import parse_layout
from pelita.game import run_game, setup_game, play_turn
from pelita.player.team import Team, split_layout_str, create_layout
from pelita.utils import setup_test_game

def stopping(bot, state):
    return bot.position, state

def randomBot(bot, state):
    legal = bot.legal_positions[:]
    return bot.random.choice(legal), state

class TestLayout:
    layout="""
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

    def test_split_layout(self):
        layout = split_layout_str(self.layout)
        assert len(layout) == 1
        assert layout[0].strip() != ""

        mini = """####
                  #  #
                  ####"""
        layout = split_layout_str(mini)
        assert len(layout) == 1
        assert layout[0].strip() != ""

    def test_load(self):
        layout = create_layout(self.layout, self.layout2)
        assert layout.bots == [(6, 1), (1, 2)]
        assert layout.enemy == [(5, 1), (2, 2)]

    def test_concat(self):
        layout = create_layout(self.layout + self.layout2)
        assert layout.bots == [(6, 1), (1, 2)]
        assert layout.enemy == [(5, 1), (2, 2)]

    def test_load1(self):
        layout = create_layout(self.layout)
        assert layout.bots == [(6, 1), (1, 2)]
        assert layout.enemy == [(5, 1), (2, 2)]

    def test_equal_positions(self):
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
        layout = create_layout(layout_str)
        assert layout.bots == [(1, 1), (1, 1)]
        assert layout.enemy ==  [(1, 1), (1, 1)]
        setup_test_game(layout=layout_str)

    def test_define_after(self):
        layout = create_layout(self.layout, food=[(1, 1)], bots=[None, None], enemy=None)
        assert layout.bots == [(6, 1), (1, 2)]
        assert layout.enemy == [(5, 1), (2, 2)]
        layout = create_layout(self.layout, food=[(1, 1)], bots=[None, (1, 2)], enemy=None)
        assert layout.bots == [(6, 1), (1, 2)]
        assert layout.enemy == [(5, 1), (2, 2)]

        layout = create_layout(self.layout, food=[(1, 1)], bots=[None, (1, 2)], enemy=[(5, 1)])
        assert layout.enemy == [(2, 2), (5, 1)]

        layout = create_layout(self.layout2, food=[(1, 1)], bots=[None, (1, 2)], enemy=[(5, 1), (2, 2)])
        assert layout.bots == [None, (1, 2)]
        assert layout.enemy == [(5, 1), (2, 2)]

        with pytest.raises(ValueError):
            # placed bot on walls
            layout = create_layout(self.layout2, food=[(1, 1)], bots=[(0, 1), (1, 2)], enemy=[(5, 1), (2, 2)])

        with pytest.raises(ValueError):
            # placed bot outside maze
            layout = create_layout(self.layout2, food=[(1, 1)], bots=[(1, 40), (1, 2)], enemy=[(5, 1), (2, 2)])

        with pytest.raises(ValueError):
            # too many bots
            layout = create_layout(self.layout2, food=[(1, 1)], bots=[(1, 1), (1, 2), (2, 2)], enemy=[(5, 1), (2, 2)])

    def test_repr(self):
        layout = create_layout(self.layout, food=[(1, 1)], bots=[None, None], enemy=None)
        assert layout._repr_html_()
        str1 = str(create_layout(self.layout, food=[(1, 1)], bots=[None, None], enemy=None))
        assert str1 == """
########
#.###  #
#      #
########

########
# ###E0#
#1E    #
########

"""

        layout_merge = create_layout(self.layout, food=[(1, 1)], bots=[(1, 2), (1, 2)], enemy=[(1, 1), (1, 1)])
        str2 = str(layout_merge)
        assert str2 == """
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
        assert create_layout(str2) == layout_merge

    def test_solo_bot(self):
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
        layout = create_layout(l, food=[(1, 1)], bots=[None, None], enemy=None)
        assert layout._repr_html_()
        str1 = str(create_layout(l, food=[(1, 1)], bots=[None, None], enemy=None))
        assert str1 == """
########
#.###  #
#      #
########

########
# ###  #
#0E    #
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
        state = run_game(team, max_rounds=1, layout_dict=parse_layout(test_layout))
        assert state['bots'][0] == (1, 1)
        assert state['bots'][1] == (10, 1)
        assert round_counting._storage['rounds'] == 1

        round_counting = self.round_counting()
        team = [
            stopping,
            round_counting
        ]
        state = run_game(team, max_rounds=3, layout_dict=parse_layout(test_layout))
        assert state['bots'][0] == (1, 1)
        assert state['bots'][1] == (10, 1)
        assert round_counting._storage['rounds'] == 3


def test_track_and_kill_count():
    # for each team, we track whether they have been eaten at least once
    # and count the number of times they have been killed
    bot_states = {
        0: [{'track': [], 'eaten': False, 'times_killed': 0}, {'track': [], 'eaten': False, 'times_killed': 0}],
        1: [{'track': [], 'eaten': False, 'times_killed': 0}, {'track': [], 'eaten': False, 'times_killed': 0}]
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
       
        if bot.eaten:
            state[turn]['eaten'] = True
            state[turn]['times_killed'] += 1
        if other.eaten:
            state[1 - turn]['eaten'] = True
            state[1 - turn]['times_killed'] += 1

        if bot.eaten or not state[turn]['track']:
            state[turn]['track'] = [bot.position]
        if other.eaten or not state[1 - turn]['track']:
            state[1 - turn]['track'] = [other.position]
        else:
            state[1 - turn]['track'].append(other.position)

        # The assertion is that the first position in bot.track
        # is always the respawn position.
        # However, in our test case, this will only happen, once
        # a bot has been eaten.
        if state[turn]['eaten']:
            assert bot.track[0] == bot.initial_position
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
        state = play_turn(state)
        # Check that our count is consistent with what the game thinks
        # for each team, we have to subtract the kills that are still in state['respawned'],
        # as they have not been passed to the bot yet
        respawned_0 = sum(state['respawned'][0::2])
        sum_killed_0 = bot_states[0][0]['times_killed'] + bot_states[0][1]['times_killed']
        assert state['deaths'][0] - respawned_0 == sum_killed_0
        respawned_1 = sum(state['respawned'][1::2])
        sum_killed_1 = bot_states[1][0]['times_killed'] + bot_states[1][1]['times_killed']
        assert state['deaths'][1] - respawned_1 == sum_killed_1

        # assertions might have been caught in run_game
        # check that all is good
        assert state['fatal_errors'] == [[], []]
