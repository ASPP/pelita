from pelita.datamodel import CTFUniverse, east, stop, west
from pelita.game_master import GameMaster
from pelita.player import SimpleTeam
from pelita.player import NQRandomPlayer, SANE_PLAYERS


class TestNQRandom_Player:
    def test_demo_players(self):
        test_layout = (
        """ ############
            #0#.   .# 1#
            ############ """)
        team = [
            SimpleTeam(NQRandomPlayer()),
            SimpleTeam(NQRandomPlayer())
        ]
        gm = GameMaster(test_layout, team, 2, 1)
        gm.play()
        assert gm.universe.bots[0].current_pos == (1, 1)
        assert gm.universe.bots[1].current_pos == (9, 1)

    def test_path(self):
        test_layout = (
        """ ############
            #  . # .# ##
            # ## #  # ##
            #0#.   .##1#
            ############ """)
        team = [
            SimpleTeam(NQRandomPlayer()),
            SimpleTeam(NQRandomPlayer())
        ]
        gm = GameMaster(test_layout, team, 2, 7)
        gm.play()
        assert gm.universe.bots[0].current_pos == (4, 3)
        assert gm.universe.bots[1].current_pos == (10, 3)

class TestPlayers:
    # Simple checks that the players are running to avoid API discrepancies
    def test_players(self):
        test_layout = (
        """ ############
            #  . # .  ##
            # ## #    ##
            # ## #  # ##
            # ## #  # ##
            #    #  # ##
            #0#.   .  1#
            ############ """)
        
        for player in SANE_PLAYERS:
            team = [
                SimpleTeam(player()),
                SimpleTeam(NQRandomPlayer())
            ]
            gm = GameMaster(test_layout, team, 2, 20)
            gm.play()
            assert gm.finished is True

