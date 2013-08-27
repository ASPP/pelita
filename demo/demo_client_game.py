# -*- coding: utf-8 -*-

from pelita.player import SimpleTeam
from players import RandomPlayer, BFSPlayer

from pelita.simplesetup import SimpleClient

import logging
from pelita.utils.colorama_wrapper import colorama

FORMAT = '[%(asctime)s,%(msecs)03d][%(name)s][%(levelname)s][%(funcName)s]' + colorama.Fore.MAGENTA + ' %(message)s' + colorama.Fore.RESET
#logging.basicConfig(format=FORMAT, datefmt="%H:%M:%S", level=logging.WARNING)


team1 = SimpleTeam("the good ones", BFSPlayer(), BFSPlayer())
client1 = SimpleClient(team1, address="tcp://localhost:50007")

team2 = SimpleTeam("the bad ones", BFSPlayer(), BFSPlayer())
client2 = SimpleClient(team2, address="tcp://localhost:50008")

client1.autoplay_process()
client2.autoplay_process()

