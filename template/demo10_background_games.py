# Run this script with
#
# python3 demo10_background_games.py
#
# - Run 100 games in the background to gather statistics
# - We'll use a team of basic defenders against a team of basic attackers
import random

import pelita.layout
import pelita.game

from demo05_basic_defender import move as move_defender
from demo04_basic_attacker import move as move_attacker

NUM_GAMES = 100

statistics = {'defender_wins': 0, 'attacker_wins': 0, 'draws': 0}

for idx in range(NUM_GAMES):
    # shuffle the color of the teams
    defenders_index = random.choice((0, 1))
    attackers_index = 1 - defenders_index

    # set up the teams
    teams = [None, None]
    team_names = [None, None]
    teams[defenders_index] = move_defender
    teams[attackers_index] = move_attacker
    team_names[defenders_index] = 'defenders'
    team_names[attackers_index] = 'attackers'

    # use a different random layout every time
    # use the same kinf of layouts that will be used in the tournament
    layout_name, layout_string = pelita.layout.get_random_layout(filter='normal_without_dead_ends')

    # run a game
    game_state = pelita.game.run_game(teams, max_rounds=300, layout_name=layout_name,
                                      layout_dict=pelita.layout.parse_layout(layout_string),
                                      team_names=team_names)

    # after the game is finished, update the stats
    if game_state['whowins'] == defenders_index:
        statistics['defender_wins'] += 1
    elif game_state['whowins'] == attackers_index:
        statistics['attacker_wins'] += 1
    else:
        statistics['draws'] += 1

print(statistics)


