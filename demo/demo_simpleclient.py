# -*- coding: utf-8 -*-

"""
We start a client using the SimpleClient class and
a couple of previously defined Players.
"""

from pelita.simplesetup import SimpleClient
from pelita.player import SimpleTeam, BFSPlayer, BasicDefensePlayer

# Set up our team named ‘the good ones’ using a
# BFSPlayer and a NQRandomPlayer.
client = SimpleClient("the good ones", SimpleTeam(BFSPlayer(), BasicDefensePlayer()))

# We could also have added more specific information about the server,
# we’d like to connect to:
# client = SimpleClient("the good ones", SimpleTeam(BFSPlayer(), NQRandomPlayer()),
#                       host="pelita.server.example.com",
#                       port=63920)

# Now, we just start the client.
# This method will only return, if the client is interrupted or closes.
client.autoplay()

