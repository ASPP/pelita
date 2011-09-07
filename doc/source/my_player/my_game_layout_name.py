#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pelita.simplesetup import SimpleClient, SimpleServer
from pelita.player import SimpleTeam, BFSPlayer, BasicDefensePlayer
from my_player import MyPlayer

# setup you own team
my_client = SimpleClient(
        SimpleTeam("my team", MyPlayer(), MyPlayer()))
my_client.autoplay_background()

# fight against two strong opponents
enemy_team = SimpleClient(
        SimpleTeam("the enemy", BFSPlayer(), BasicDefensePlayer()))
enemy_team.autoplay_background()

server = SimpleServer(layout_name='layout_01_demo')
server.run_tk()
