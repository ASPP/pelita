# We build a team of bots, one basic defender and one basic attacker
TEAM_NAME = 'one and one'

from demo05_basic_defender import move as move_defender
from demo04_basic_attacker import move as move_attacker
from talk_util import say_underlined

def move(bot, state):
    # Keep two "substates" — one for each bot
    if state == {}:
        state['attacker'] = {}
        state['defender'] = {}

    if bot.turn == 0:
        next_pos = move_defender(bot, state['defender'])
        if bot.round < 10:
            say_underlined(bot, 'defender')
    else:
        next_pos = move_attacker(bot, state['attacker'])
        if bot.round < 10:
            say_underlined(bot, 'attacker')

    return next_pos
