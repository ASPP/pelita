#!/usr/bin/python
from pelita.game_master import GameMaster
from pelita.player import StoppingPlayer, SimpleTeam
from pelita.viewer import AsciiViewer

LAYOUT="""
##################################
#...   #      .#     #  #       3#
# ## #   # ###    #  #     #####1#
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
#0#####     #  #    ### #   # ## #
#2       #  #     #.      #   ...#
##################################
##################################
#...   #      .#     #  #        #
# ## #   # ###    #  #     ##### #
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
# #####     #  #    ### #   # ## #
#        #  #     #.      #   ...#
##################################
"""

if __name__ == '__main__':
    import time
    start = time.time()
    layout = LAYOUT
    gm = GameMaster(layout, 4, 10)
    gm.register_team(SimpleTeam(StoppingPlayer(), StoppingPlayer()))
    gm.register_team(SimpleTeam(StoppingPlayer(), StoppingPlayer()))
    #gm.register_viewer(AsciiViewer())
    gm.play()
    print(len(LAYOUT), time.time() - start)
