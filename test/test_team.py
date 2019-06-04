import pytest

from pelita.datamodel import CTFUniverse
from pelita.game_master import GameMaster
from pelita.player.team import Team, split_layout_str, create_layout
from pelita.utils import setup_test_game

def stopping(bot, state):
    return (0, 0), state

def randomBot(bot, state):
    legal = bot.legal_moves[:]
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
            return (0, 0), state
        inner._storage = storage_copy
        return inner

    def test_stopping(self):
        test_layout = (
        """ ############
            #0#.23 .# 1#
            ############ """)

        round_counting = self.round_counting()
        team = [
            Team(stopping),
            Team(round_counting)
        ]
        gm = GameMaster(test_layout, team, 4, 1)
        gm.play()
        universe = CTFUniverse._from_json_dict(gm.game_state)
        assert universe.bots[0].current_pos == (1, 1)
        assert universe.bots[1].current_pos == (10, 1)
        assert round_counting._storage['rounds'] == 1


        round_counting = self.round_counting()
        team = [
            Team(stopping),
            Team(round_counting)
        ]
        gm = GameMaster(test_layout, team, 4, 3)
        gm.play()
        universe = CTFUniverse._from_json_dict(gm.game_state)
        print(universe.pretty)
        assert universe.bots[0].current_pos == (1, 1)
        assert universe.bots[1].current_pos == (10, 1)
        assert round_counting._storage['rounds'] == 3


class TestTrack:
    def test_track(self):
        def trackingBot(bot, state):
            turn = bot.turn
            other = bot.other
            if bot.round == 0 and turn == 0:
                assert bot.track[0] == bot.position
                state = {}
                state[turn] = {}
                state[1 - turn] = {}
                state[turn]['track'] = []
                state[1 - turn]['track'] = []

            if bot.eaten or not state[turn]['track']:
                state[turn]['track'] = [bot.position]
            if other.eaten or not state[1 - turn]['track']:
                state[1 - turn]['track'] = [other.position]
            else:
                state[1 - turn]['track'].append(other.position)

            assert bot.track[0] == bot._initial_position
            assert bot.track == state[turn]['track'] # bot.round * 2 + 1 + turn
            assert bot.track[-1] == bot.position
            return randomBot(bot, state)

        layout = """
        ############
        ##02   .3 1#
        ############
        #.#      #.#
        ############
        """
        team = [
            Team(trackingBot),
            Team(trackingBot)
        ]
        gm = GameMaster(layout, team, 4, 300)
        gm.play()
