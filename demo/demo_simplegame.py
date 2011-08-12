# -*- coding: utf-8 -*-

"""
Defining a game server and clients in one and the same file is also possible.
(For setup using multiple files, see demo_simpleclient.py and demo_simpleserver.py.)

The important difference here, is the order of actions.
Since the TkViewer needs to run in the main thread, it must be the last
action in this file. (Otherwise, we would have to wait for it to close again.)

This is not so much of a problem, though, since our clients may run in
background processes (using autoplay_background() instead of autoplay()).
There is a smaller problem with this: If we start the client before the server,
our client might try to connect before the server is ready. This is ‘fixed’
repeated tries and should not be a problem in general.

"""

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

