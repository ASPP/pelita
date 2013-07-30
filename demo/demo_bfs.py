#!/usr/bin/python
from pelita.game_master import GameMaster
from pelita.player import StoppingPlayer, BFSPlayer, Squad
from pelita.viewer import AsciiViewer

if __name__ == '__main__':
    layout = (
        """ ##################
            #0#.  .  # .     #
            # #####    ##### #
            #     . #  .  .#1#
            ################## """)
    gm = GameMaster(layout, 2, 200)
    gm.register_team(Squad(BFSPlayer()))
    gm.register_team(Squad(StoppingPlayer()))
    gm.register_viewer(AsciiViewer())
    gm.play()
