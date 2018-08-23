# We build a team of bots, one basic defender and one basic attacker
TEAM_NAME = 'one and one'

from demo05_basic_defender import move as move_defender
from demo04_basic_attacker import move as move_attacker

def move(turn, game):
    if game.state is None:
        one_by_one_state = {'attacker' : None, 'defender' : None}
    else:
        one_by_one_state = game.state

    if turn == 0:
        game.state = one_by_one_state['defender']
        next_move = move_defender(turn, game)
    else:
        game.state = one_by_one_state['attacker']
        next_move = move_attacker(turn, game)

    # reset the game state
    game.state = one_by_one_state

    return next_move
