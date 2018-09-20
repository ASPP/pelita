# We build a team of bots, one basic defender and one basic attacker
TEAM_NAME = 'one and one'

from demo05_basic_defender import move as move_defender
from demo04_basic_attacker import move as move_attacker

def move(bot, state):
    # create a combined game state to collect the states for both bots
    if state is None:
        # initialization
        state = {'attacker' : None, 'defender' : None}

    if bot.turn == 0:
        # ignore returned state from defender, we store it in our
        # state dictionary anyway
        next_move, _ = move_defender(bot, state['defender'])
    else:
        # same as above
        next_move, _ = move_attacker(bot, state['attacker'])

    return next_move, state
