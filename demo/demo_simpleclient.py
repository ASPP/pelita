"""
We start a client using the SimpleClient class and
a couple of previously defined Players.
"""

from pelita.simplesetup import SimpleClient
from pelita.player import SimpleTeam
from players import BFSPlayer, BasicDefensePlayer

# Set up our team named ‘the good ones’ using a
# BFSPlayer and a NQRandomPlayer.
client = SimpleClient(SimpleTeam("the good ones", BFSPlayer(), BasicDefensePlayer()), address="tcp://localhost:50210")

# Now, we just start the client.
# This method will only return, if the client is interrupted or closes.
client.run()

