# -*- coding: utf-8 -*-

"""
We start a server using the SimpleServer class and a layout
given by the specified layout file.
"""

from pelita.simplesetup import SimpleServer

server = SimpleServer(layoutfile="layouts/02.layout")
# For more control, we could also define a game with 8 Bots,
# run 10000 rounds and want to receive connections on port
#
# server = SimpleServer(layoutfile="layouts/02.layout", players=8, rounds=10000, port=61009)

# Now we run it with a Tk interface.
# This will only ever return if interrupted or if Tk is closed.
server.run_tk()

