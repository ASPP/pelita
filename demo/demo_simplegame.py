# -*- coding: utf-8 -*-

from pelita.simplesetup import SimpleClient, SimpleServer

from pelita.player import RandomPlayer, BFSPlayer, SimpleTeam, StoppingPlayer, NQRandomPlayer

import multiprocessing

client = SimpleClient("the good ones", SimpleTeam(NQRandomPlayer(), NQRandomPlayer()))
t = multiprocessing.Process(target=client.autoplay)
t.start()

client2 = SimpleClient("the bad ones", SimpleTeam(NQRandomPlayer(), NQRandomPlayer()))
t = multiprocessing.Process(target=client2.autoplay)
t.start()

layout ="""
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


server = SimpleServer(layout=layout, rounds=50)
server.run_tk()


