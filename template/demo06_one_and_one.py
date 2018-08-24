# We build a team of bots, one basic defender and one basic attacker
TEAM_NAME = 'one and one'

from demo05_basic_defender import move as move_defender
from demo04_basic_attacker import move as move_attacker

def move(turn, game):
    # create a combined game state to collect the states for both bots
    if game.state is None:
        # initialization
        combined_state = {'attacker' : None, 'defender' : None}
    else:
        # keep a copy of the game state (the move_defender and move_attacker
        # functions are going to overwrite game.state, so we need a copy
        # here so that we can reset game.state before returning)
        combined_state = game.state.copy()

    if turn == 0:
        # fake the game.state
        game.state = combined_state['defender']
        next_move = move_defender(turn, game)
        # collect the defender state in our own dictionary
        combined_state['defender'] = game.state
    else:
        # same as above
        game.state = combined_state['attacker']
        next_move = move_attacker(turn, game)
        # collect the attacker state in our own dictionary
        combined_state['attacker'] = game.state

    game.state = combined_state

    return next_move
