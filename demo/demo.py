#!/usr/bin/env python3
# -*- coding: utf-8 -*-


""" This file demonstrates setting up a server and two clients using local actor
connections.  The order is important in this case (as is described in
demo_simplegame.py).

A difference to the remote game in demo_simplegame is that now,
`client.autoplay_background` uses a background thread instead of a background
process. This background thread sometimes does not close on CTRL+C. In these
cases, pressing CTRL+Z and then entering ‘kill %%’ usually is the way to get rid
of the program. """

from pelita.simplesetup import SimpleClient, SimpleServer
from pelita.player import RandomPlayer, NQRandomPlayer,\
    BFSPlayer, BasicDefensePlayer, SimpleTeam

client = SimpleClient(
        SimpleTeam("the good ones", RandomPlayer(), NQRandomPlayer()))
client.autoplay_background()

client2 = SimpleClient(
        SimpleTeam("the bad ones", BFSPlayer(), BasicDefensePlayer()))
client2.autoplay_background()

server = SimpleServer()
server.run_tk()

