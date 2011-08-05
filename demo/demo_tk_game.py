#!/usr/bin/python
import threading

from pelita.game_master import GameMaster
from pelita.player import StoppingPlayer, RandomPlayer, NQRandomPlayer, BFSPlayer, SimpleTeam
from pelita.ui.tk_viewer import TkViewer

if __name__ == '__main__':
    layout = (
        """ ##################
            #0#.  .  # .     #
            #2#####    #####1#
            #     . #  .  .#3#
            ################## """)
    gm = GameMaster(layout, 4, 200)
    gm.register_team(SimpleTeam(StoppingPlayer(), NQRandomPlayer()))
    gm.register_team(SimpleTeam(RandomPlayer(), BFSPlayer()))

    viewer = TkViewer()

    gm.register_viewer(viewer)

    threading.Thread(target=gm.play).start()

    viewer.viewer.mainloop()
