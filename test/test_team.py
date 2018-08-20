import pytest

from pelita.game_master import GameMaster
from pelita.player import Team
from pelita.utils import create_layout, setup_test_game

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

    def test_load(self):
        layout = create_layout(self.layout, self.layout2)
        assert layout.bots == [(6, 1), (1, 2)]
        assert layout.enemy == [(5, 1), (2, 2)]
    
    def test_concat(self):
        layout = create_layout(self.layout + self.layout2)
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
        setup_test_game(layout=layout) 

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

        with pytest.raises(KeyError):
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



class TestStoppingTeam:
    @staticmethod
    def stopping(turn, game):
        return (0, 0)

    @staticmethod
    def round_counting():
        storage_copy = {}
        def inner(turn, game):
            game.state[turn] = game.state.get(turn, 0) + 1
            storage_copy['rounds'] = game.state[turn]
            return (0, 0)
        inner._storage = storage_copy
        return inner

    def test_stopping(self):
        test_layout = (
        """ ############
            #0#.   .# 1#
            ############ """)

        round_counting = self.round_counting()
        team = [
            Team(self.stopping),
            Team(round_counting)
        ]
        gm = GameMaster(test_layout, team, 2, 1)
        gm.play()
        assert gm.universe.bots[0].current_pos == (1, 1)
        assert gm.universe.bots[1].current_pos == (10, 1)
        assert round_counting._storage['rounds'] == 1


        round_counting = self.round_counting()
        team = [
            Team(self.stopping),
            Team(round_counting)
        ]
        gm = GameMaster(test_layout, team, 2, 3)
        gm.play()
        assert gm.universe.bots[0].current_pos == (1, 1)
        assert gm.universe.bots[1].current_pos == (10, 1)
        assert round_counting._storage['rounds'] == 3
