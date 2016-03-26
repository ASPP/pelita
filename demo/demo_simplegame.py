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

On certain operating systems (at least on Windows), starting processes naïvely
may spark a fork bomb. Therefore, all scripts using multiprocessing must use
a __name__=="__main__" part to shield from multiple execution of the script
when a new process is started.

"""

from pelita.simplesetup import SimpleClient, SimpleServer
from pelita.player import SimpleTeam
from players import RandomPlayer, BFSPlayer, BasicDefensePlayer, NQRandomPlayer

if __name__=="__main__":
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

    server = SimpleServer(layout_string=layout, rounds=3000)

    def star_to_localhost(str):
        # server might publish to tcp://* in which case we simply try localhost for the clients
        return str.replace("*", "localhost")

    client = SimpleClient(SimpleTeam("the good ones", NQRandomPlayer(), BFSPlayer()), address=star_to_localhost(server.bind_addresses[0]))
    client.autoplay_process()

    client2 = SimpleClient(SimpleTeam("the bad ones", BFSPlayer(), BasicDefensePlayer()), address=star_to_localhost(server.bind_addresses[1]))
    client2.autoplay_process()

    server.run()
    print(server.game_master.universe.pretty)
    print(server.game_master.game_state)

