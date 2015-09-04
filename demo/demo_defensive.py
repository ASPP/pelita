#!/usr/bin/env python3
from pelita.game_master import GameMaster
from pelita.player import SimpleTeam, StoppingPlayer
from pelita.viewer import AsciiViewer
from pelita.layout import get_random_layout
from players import BFSPlayer, BasicDefensePlayer

if __name__ == '__main__':
    name, layout = get_random_layout()
    gm = GameMaster(layout, 4, 200)
    gm.register_team(SimpleTeam(BFSPlayer(), BFSPlayer()))
    gm.register_team(SimpleTeam(BasicDefensePlayer(), BasicDefensePlayer()))
    gm.register_viewer(AsciiViewer())
    gm.play()
