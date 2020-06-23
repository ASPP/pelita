#!/usr/bin/env python3

from pelita.layout import parse_layout
from pelita.game import run_game
from pelita.player import smart_eating_player, smart_random_player

if __name__ == '__main__':
    layout = parse_layout(
        """ ##################
            #a#.  .  # .     #
            #b#####    #####y#
            #     . #  .  .#x#
            ################## """)

    teams = [smart_eating_player, smart_random_player]
    run_game(teams, layout_dict=layout, max_rounds=200, viewers=['ascii'])
