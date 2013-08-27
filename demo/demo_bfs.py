#!/usr/bin/python
from pelita.game_master import GameMaster
from pelita.player import StoppingPlayer, SimpleTeam
from pelita.viewer import AsciiViewer
from players import BFSPlayer

if __name__ == '__main__':
    layout = (
        """ ##################
            #0#.  .  # .     #
            # #####    ##### #
            #     . #  .  .#1#
            ################## """)
    gm = GameMaster(layout, 2, 200)
    gm.register_team(SimpleTeam(BFSPlayer()))
    gm.register_team(SimpleTeam(StoppingPlayer()))
    gm.register_viewer(AsciiViewer())
    gm.play()
