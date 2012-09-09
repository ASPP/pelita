# -*- coding: utf-8 -*-

"""
This is a more verbose demonstration, which describes how to play a game
using local actors.

In general, the simplesetup methods should be sufficient.

Note: When a game runs, the ServerActor gives all control to
the game_master, so it is not possible to query (or stop)
the actor anymore until the game has finished.
"""


from pelita.messaging import actor_of
from pelita.actors import ServerActor
from pelita.ui.tk_viewer import TkViewer

from pelita.player import RandomPlayer, BFSPlayer, SimpleTeam

from pelita.actors import ClientActor

# Instantiate the ServerActor and start it.
server = actor_of(ServerActor, "pelita-main")
server.start()

layout = (
        """ ##################
            #0#.  . 2# .   3 #
            # #####    ##### #
            #     . #  .  .#1#
            ################## """)

# Notify the ServerActor that we’d like to run a game
# with our preferred layout, 4 bots and 200 rounds.
server.notify("initialize_game", [layout, 4, 200])

# Initialise a TkViewer and register it with the ServerActor.
viewer = TkViewer()
server.notify("register_viewer", [viewer])

# Our two PlayerTeams must be defined in the same Python
# process (because this is local game).
# Create their ClientActors, register the Teams, and connect
# to the ServerActor.
clientActor = ClientActor("the good ones")
clientActor.register_team(SimpleTeam(BFSPlayer(), BFSPlayer()))
clientActor.connect_local("pelita-main")

clientActor2 = ClientActor("the bad ones")
clientActor2.register_team(SimpleTeam(RandomPlayer(), RandomPlayer()))
clientActor2.connect_local("pelita-main")

# Now follows the boilerplate which is needed to run the game.
# As this uses a TkViewer, we need to give Tk the control
# over our main thread.
# Since everything else runs in threaded actors, this is not
# much of a problem. The queue needed to exchange data between
# different threads is handled by our TkViewer.
try:
    viewer.root.mainloop()
except KeyboardInterrupt:
    print("Received CTRL+C. Exiting.")
finally:
    # Finally, we need to ensure that everything closes.

    clientActor.actor_ref.stop()
    clientActor2.actor_ref.stop()

    server.stop()
