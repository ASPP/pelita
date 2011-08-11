# -*- coding: utf-8 -*-

from pelita.simplesetup import SimpleClient
from pelita.player import SimpleTeam, BFSPlayer, NQRandomPlayer

client = SimpleClient("the good ones", SimpleTeam(BFSPlayer(), NQRandomPlayer()))
# client.host = "pelita.server.example.com"
# client.port = 50011
client.autoplay()

