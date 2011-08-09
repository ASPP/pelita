
from pelita.messaging import actor_of, RemoteConnection
from pelita.actors import ServerActor
import logging
from pelita.ui.tk_viewer import TkViewer

from pelita.utils.colorama_wrapper import colorama

FORMAT = '[%(asctime)s,%(msecs)03d][%(name)s][%(levelname)s][%(funcName)s]' + colorama.Fore.MAGENTA + ' %(message)s' + colorama.Fore.RESET
#logging.basicConfig(format=FORMAT, datefmt="%H:%M:%S", level=logging.WARNING)

server = actor_of(ServerActor, "pelita-main")


remote = RemoteConnection().start_listener(host="", port=50007)
remote.register("pelita-main", server)
remote.start_all()

#server.start()

layout = (
        """ ##################
            #0#.  . 2# .   3 #
            # #####    ##### #
            #     . #  .  .#1#
            ################## """)

server.notify("initialize_game", [layout, 4, 200])

viewer = TkViewer()
server.notify("register_viewer", [viewer])


try:
    viewer.app.mainloop()
except KeyboardInterrupt:
    print "Received CTRL+C. Exiting."
finally:
    server.stop()
    remote.stop()

#remote.stop()
