#!/usr/bin/python
from pelita.game_master import GameMaster
from pelita.player import RandomPlayer
from pelita.viewer import AsciiViewer

if __name__ == '__main__':
    layout = (
        """ ##################
            #0#.  .  # .     #
            #2#####    #####1#
            #     . #  .  .#3#
            ################## """)
    gm = GameMaster(layout, 4, 200)
    gm.register_player(RandomPlayer())
    gm.register_player(RandomPlayer())
    gm.register_player(RandomPlayer())
    gm.register_player(RandomPlayer())
    gm.register_viewer(AsciiViewer())
    gm.play()
