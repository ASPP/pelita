#!/usr/bin/python
from pelita.game_master import GameMaster
from pelita.player import BFSPlayer, BasicDefensePlayer, Squad, StoppingPlayer
from pelita.viewer import AsciiViewer
from pelita.layout import get_layout_by_name

if __name__ == '__main__':
    layout = get_layout_by_name('layout_01_demo')
    gm = GameMaster(layout, 4, 200)
    gm.register_team(Squad(BFSPlayer(), BFSPlayer()))
    gm.register_team(Squad(BasicDefensePlayer(), BasicDefensePlayer()))
    gm.register_viewer(AsciiViewer())
    gm.play()
