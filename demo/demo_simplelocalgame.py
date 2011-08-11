# -*- coding: utf-8 -*-

from pelita.simplesetup import SimpleClient, SimpleServer
from pelita.player import RandomPlayer, BFSPlayer, SimpleTeam, StoppingPlayer, NQRandomPlayer

client = SimpleClient("the good ones", SimpleTeam(NQRandomPlayer(), RandomPlayer()), local=True)
client.autoplay_background()

client2 = SimpleClient("the bad ones", SimpleTeam(BFSPlayer(), StoppingPlayer()), local=True)
client2.autoplay_background()

server = SimpleServer(layoutfile="layouts/01.layout", rounds=3000, local=True)
server.run_tk()

