#!/usr/bin/python
from pelita.game_master import GameMaster
from pelita.player import BFSPlayer, BasicDefensePlayer, SimpleTeam, StoppingPlayer
from pelita.viewer import AsciiViewer

if __name__ == '__main__':
    with open('layouts/01.layout') as layout_file:
        layout = layout_file.read()
    gm = GameMaster(layout, 4, 200)
    gm.register_team(SimpleTeam(BFSPlayer(), StoppingPlayer()))
    gm.register_team(SimpleTeam(BasicDefensePlayer(), StoppingPlayer()))
    gm.register_viewer(AsciiViewer())
    gm.play()
