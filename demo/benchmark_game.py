#!/usr/bin/env python3

from pelita.layout import parse_layout
from pelita.game import run_game
from pelita.player import stopping_player

LAYOUT="""
##################################
#...   #      .#     #  #       y#
# ## #   # ###    #  #     #####x#
#.   # #    # .   # ##           #
#.#    #  .    #    .  # #########
# ## # ## ####    # ##.   . .   .#
#.. .  .  #. . #. #  # ## #####  #
# ## #### #.## #     #  .  . . ..#
#..  ..   # #  #  #    ##### #####
##### #####    #  #  # #   ..  ..#
#.. . .  .  #     # ##.# #### ## #
#  ##### ## #  # .# . .#  .  . ..#
#.   . .   .## #    #### ## # ## #
######### #  .    #    .  #    #.#
#           ## #   . #    # #   .#
#a#####     #  #    ### #   # ## #
#b       #  #     #.      #   ...#
##################################
"""

layout = parse_layout(LAYOUT)

def run():
    return run_game([stopping_player, stopping_player], max_rounds=10, layout_dict=layout)

if __name__ == '__main__':
    import timeit
    REPEAT = 5
    NUMBER = 10
    result = min(timeit.repeat(run, repeat=REPEAT, number=NUMBER))
    print("Fastest out of {}: {}".format(REPEAT, result))

    import cProfile
    cProfile.runctx("""run()""", globals(), locals())
