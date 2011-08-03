from pelita.player import RandomPlayer

from pelita.actors import ClientActor

import logging
from pelita.utils.colorama_wrapper import colorama

FORMAT = '[%(asctime)s,%(msecs)03d][%(name)s][%(levelname)s][%(funcName)s]' + colorama.Fore.MAGENTA + ' %(message)s' + colorama.Fore.RESET
#logging.basicConfig(format=FORMAT, datefmt="%H:%M:%S", level=logging.WARNING)

import demo_server_game

clientActor = ClientActor("the good ones")
clientActor.register_player(RandomPlayer())
clientActor.connect("pelita-main")

clientActor2 = ClientActor("the bad ones")
clientActor2.register_player(RandomPlayer())
clientActor2.connect("pelita-main")

