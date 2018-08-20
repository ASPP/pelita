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
        assert layout.bot_positions == {'0': (6, 1), '1': (1, 2), 'E': [(5, 1), (2, 2)]}
    
    def test_concat(self):
        layout = create_layout(self.layout + self.layout2)
        assert layout.bot_positions == {'0': (6, 1), '1': (1, 2), 'E': [(5, 1), (2, 2)]}
    
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
        assert layout.bot_positions == {'0': (1, 1), '1': (1, 1), 'E': [(1, 1), (1, 1)]}
        setup_test_game(layout=layout) 


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
