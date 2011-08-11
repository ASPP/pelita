# -*- coding: utf-8 -*-

from pelita.messaging import actor_of
from pelita.actors import ServerActor
from pelita.ui.tk_viewer import TkViewer

from pelita.player import RandomPlayer, BFSPlayer, SimpleTeam

from pelita.actors import ClientActor

server = actor_of(ServerActor, "pelita-main")
server.start()

layout = (
        """ ##################
            #0#.  . 2# .   3 #
            # #####    ##### #
            #     . #  .  .#1#
            ################## """)

server.notify("initialize_game", [layout, 4, 200])

viewer = TkViewer()
server.notify("register_viewer", [viewer])

clientActor = ClientActor("the good ones")
clientActor.register_team(SimpleTeam(BFSPlayer(), BFSPlayer()))
clientActor.connect_local("pelita-main")

clientActor2 = ClientActor("the bad ones")
clientActor2.register_team(SimpleTeam(RandomPlayer(), RandomPlayer()))
clientActor2.connect_local("pelita-main")

try:
    viewer.app.mainloop()
except KeyboardInterrupt:
    print "Received CTRL+C. Exiting."
finally:
    clientActor.actor_ref.stop()
    clientActor2.actor_ref.stop()

    server.stop()
