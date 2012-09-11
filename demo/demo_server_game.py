# -*- coding: utf-8 -*-

"""
Verbose demonstration of how to set up a server and run a remote game.

For all practical needs, using the simplesetup module should be sufficient.
"""

import sys
import subprocess

from pelita.messaging import actor_of, RemoteConnection
from pelita.simplesetup import SimpleServer, SimplePublisher, SimpleController
import logging
from pelita.ui.tk_viewer import TkViewer

from pelita.utils.colorama_wrapper import colorama

def get_python_process():
    py_proc = sys.executable
    if not py_proc:
        raise RuntimeError("Cannot retrieve current Python executable.")
    return py_proc

FORMAT = '[%(asctime)s,%(msecs)03d][%(name)s][%(levelname)s][%(funcName)s]' + colorama.Fore.MAGENTA + ' %(message)s' + colorama.Fore.RESET
logging.basicConfig(format=FORMAT, datefmt="%H:%M:%S", level=logging.INFO)

layout = (
        """ ##################
            #0#.  . 2# .   3 #
            # #####    ##### #
            #     . #  .  .#1#
            ################## """)

server = SimpleServer(layout_string=layout, rounds=200, bind_addrs=("tcp://*:50007", "tcp://*:50008"))

publisher = SimplePublisher("tcp://*:50012")
server.game_master.register_viewer(publisher)

subscribe_sock = server
tk_open = "TkViewer(%r, %r).run()" % ("tcp://localhost:50012", "tcp://localhost:50013")
tkprocess = subprocess.Popen([get_python_process(),
                              "-c",
                              "from pelita.ui.tk_viewer import TkViewer\n" + tk_open])

try:
    print(server.bind_addresses)
    server.register_teams()
    controller = SimpleController(server.game_master, "tcp://*:50013")
    controller.run()
    server.exit_teams()
except KeyboardInterrupt:
    tkprocess.kill()

