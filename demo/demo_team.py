
import random

from pelita.player import Team
from pelita.player.player_functions import legal_moves

def move1(datadict, storage):
    legal = legal_moves(datadict)
    return random.choice(legal)

def move2(datadict, storage):
    return (0, 0)

def team():
    return Team("My Team", move1, move2)
