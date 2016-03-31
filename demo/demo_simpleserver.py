"""
We start a server using the SimpleServer class and a layout
given by the specified layout file.
"""

from pelita.simplesetup import SimpleServer
from pelita.layout import get_random_layout

layout_name, layout_string = get_random_layout()
server = SimpleServer(layout_string=layout_string, layout_name=layout_name)
# For more control, we could also define a game with 8 Bots,
# run 10000 rounds and want to receive connections on port
#
# server = SimpleServer(layout_string=layout_string, players=8, rounds=10000, port=61009, layout_name=layout_name)

server.run()

