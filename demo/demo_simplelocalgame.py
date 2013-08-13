#!/usr/bin/env python
# -*- coding: utf-8 -*-


"""
This file demonstrates setting up a server and two clients using local connections.
"""

from pelita.simplesetup import SimpleClient, SimpleServer
from pelita.player import RandomPlayer, BFSPlayer, Squad, StoppingPlayer, NQRandomPlayer, BasicDefensePlayer

client = SimpleClient(Squad("the good ones", NQRandomPlayer(), BFSPlayer()), address="ipc:///tmp/pelita-client1")
client.autoplay_process()

client2 = SimpleClient(Squad("the bad ones", BFSPlayer(), BasicDefensePlayer()), address="ipc:///tmp/pelita-client2")
client2.autoplay_process()

server = SimpleServer(rounds=3000, bind_addrs=(client.address, client2.address))
server.run()

