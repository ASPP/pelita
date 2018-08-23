import pytest

from pelita.game_master import GameMaster
from pelita.player.team import Team, split_layout_str, create_layout, _rebuild_universe, bots_from_universe
from pelita.utils import setup_test_game

def stopping(turn, game):
    return (0, 0)

def randomBot(turn, game):
    bot = game.team[turn]
    legal = bot.legal_moves[:]
    return bot.random.choice(legal)

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


class TestStoppingTeam:
    @staticmethod
    def round_counting():
        storage_copy = {}
        def inner(turn, game):
            if game.state is None:
                game.state = {}
            game.state[turn] = game.state.get(turn, 0) + 1
            storage_copy['rounds'] = game.state[turn]
            return (0, 0)
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
        assert gm.universe.bots[0].current_pos == (1, 1)
        assert gm.universe.bots[1].current_pos == (10, 1)
        assert round_counting._storage['rounds'] == 1


        round_counting = self.round_counting()
        team = [
            Team(stopping),
            Team(round_counting)
        ]
        gm = GameMaster(test_layout, team, 4, 3)
        gm.play()
        assert gm.universe.bots[0].current_pos == (1, 1)
        assert gm.universe.bots[1].current_pos == (10, 1)
        assert round_counting._storage['rounds'] == 3


class TestRebuild:
    def test_too_few_bots(self):
        test_layout = (
        """ ############
            #0#.   .# 1#
            ############ """)


        team = [
            Team(stopping),
            Team(stopping)
        ]
        gm = GameMaster(test_layout, team, 2, 1)
        with pytest.raises(IndexError):
            gm.play()

    def test_rebuild_uni(self):
        layout = """
        ############
        #0#.   .# 1#
        ############
        """
        game = setup_test_game(layout=layout, is_blue=True)
        assert game.team[0].position == (1, 1)
        assert game.team[1].position == (10, 1)
        assert game.team[0].enemy[0].position is None
        assert game.team[0].enemy[1].position is None

        uni, state = _rebuild_universe(game.team[0]._bots)
        assert uni.bots[0].current_pos == (1, 1)
        assert uni.bots[2].current_pos == (10, 1)
        assert uni.bots[1].current_pos == (9, 1)
        assert uni.bots[3].current_pos == (10, 1)

        with pytest.raises(ValueError):
            uni, state = _rebuild_universe(game.team[0]._bots[0:2])

        bots = bots_from_universe(uni, [None] * 4, round=0,
                                                   team_name=state['team_name'],
                                                   timeout_count=state['timeout_teams'])
        uni2, state = _rebuild_universe(bots)
        assert uni2 == uni


class TestTrack:
    def test_track(self):
        def trackingBot(turn, game):
            bot = game.team[turn]
            if bot.round == 0 and turn == 0:
                assert bot.track[0] == bot.position
                game.state = {}
                game.state[turn] = {}
                game.state[1 - turn] = {}
                game.state[turn]['track'] = []
                game.state[1 - turn]['track'] = []

            if bot.eaten:
                game.state[turn]['track'] = []
            if bot.other.eaten:
                game.state[1 - turn]['track'] = []

            game.state[turn]['track'].append(bot.position)
            game.state[1 - turn]['track'].append(bot.other.position)

            assert bot.track[0] == bot._initial_position
            assert bot.track == game.state[turn]['track'] # bot.round * 2 + 1 + turn
            assert bot.track[-1] == bot.position
            return randomBot(turn, game)

        layout = """
        ############
        #  #02 .3 1#
        ############
        #.#      #.#
        ############
        """
        team = [
            Team(trackingBot),
            Team(trackingBot)
        ]
        gm = GameMaster(layout, team, 4, 30)
        gm.play()
