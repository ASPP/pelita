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
        # keep the modified state from defender
        next_pos, state_defender = move_defender(bot, state['defender'])
        state['defender'] = state_defender
    else:
        # keep the modified state from attacker
        next_pos, state_attacker = move_attacker(bot, state['attacker'])
        state['attacker'] = state_attacker

    return next_pos, state
