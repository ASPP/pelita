#!/usr/bin/python
import threading

from pelita.game_master import GameMaster
from pelita.player import StoppingPlayer, RandomPlayer, NQRandomPlayer, BFSPlayer
from pelita.ui.tk_viewer import TkViewer

if __name__ == '__main__':
    layout = (
        """ ##################
            #0#.  .  # .     #
            #2#####    #####1#
            #     . #  .  .#3#
            ################## """)
    gm = GameMaster(layout, 4, 200)
    gm.register_player(StoppingPlayer())
    gm.register_player(RandomPlayer())
    gm.register_player(NQRandomPlayer())
    gm.register_player(BFSPlayer())

    viewer = TkViewer()

    gm.register_viewer(viewer)

    threading.Thread(target=gm.play).start()

    viewer.viewer.mainloop()
