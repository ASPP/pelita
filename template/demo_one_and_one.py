# We build a team of bots, one basic defender and one basic attacker
TEAM_NAME = 'one and one'

from demo_basic_defender import move as move_defender
from demo_basic_attacker import move as move_attacker

def move(turn, game):
    if turn == 0:
        return move_defender(turn, game)
    else:
        return move_attacker(turn, game)
