# -*- coding: utf-8 -*-

from pelita.simplesetup import SimpleClient, SimpleServer
from pelita.player import RandomPlayer, BFSPlayer, SimpleTeam, StoppingPlayer, NQRandomPlayer

client = SimpleClient("the good ones", SimpleTeam(NQRandomPlayer(), RandomPlayer()))
client.autoplay_background()

client2 = SimpleClient("the bad ones", SimpleTeam(BFSPlayer(), StoppingPlayer()))
client2.autoplay_background()


layout = """
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
"""

server = SimpleServer(layout=layout, rounds=3000)
server.run_tk()

