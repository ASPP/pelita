#!/usr/bin/python
from pelita.game_master import GameMaster
from pelita.player import StoppingPlayer, RandomPlayer, NQRandomPlayer, Squad
from pelita.viewer import AsciiViewer

if __name__ == '__main__':
    layout = (
        """ ##################
            #0#.  .  # .     #
            #2#####    #####1#
            #     . #  .  .#3#
            ################## """)
    gm = GameMaster(layout, 4, 200)
    gm.register_team(Squad(StoppingPlayer(), NQRandomPlayer()))
    gm.register_team(Squad(NQRandomPlayer(), NQRandomPlayer()))
    gm.register_viewer(AsciiViewer())
    gm.play()
