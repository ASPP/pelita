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

def run_game():
    layout = LAYOUT
    teams = [
        SimpleTeam(StoppingPlayer(), StoppingPlayer()),
        SimpleTeam(StoppingPlayer(), StoppingPlayer())
    ]
    gm = GameMaster(layout, teams, 4, 10)
    #gm.register_viewer(AsciiViewer())
    gm.play()

if __name__ == '__main__':
    import timeit
    REPEAT = 5
    NUMBER = 10
    result = min(timeit.repeat(run_game, repeat=REPEAT, number=NUMBER))
    print("Fastest out of {}: {}".format(REPEAT, result))

    import cProfile
    cProfile.runctx("""run_game()""", globals(), locals())
