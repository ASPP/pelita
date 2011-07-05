#!/usr/bin/python
from pelita.game_master import GameMaster, RandomPlayer, AsciiViewer

if __name__ == '__main__':
    layout = (
        """ ##################
            #0#.  .  # .     #
            #2#####    #####1#
            #     . #  .  .#3#
            ################## """)
    gm = GameMaster(layout, 4, 200)
    gm.register_player(0, RandomPlayer(0))
    gm.register_player(1, RandomPlayer(1))
    gm.register_player(2, RandomPlayer(2))
    gm.register_player(3, RandomPlayer(3))
    gm.register_viewer(AsciiViewer())
    gm.play()
