#!/usr/bin/env python3

import random

from pelita.layout import get_random_layout, parse_layout
from pelita.game import run_game
from pelita.player import smart_eating_player, smart_random_player

# This demo assumes that we are the smart_eating_player and want 
# to find out who is best by playing against the smart_random_player

# play 100 games
NUM_GAMES = 100

# our move function:
def move(bot, state):
    return smart_eating_player(bot, state)

# our enemy
enemy_move = smart_random_player

   
statistics = {'wins': 0, 'draws': 0, 'losses': 0}

for m in range(NUM_GAMES):
    # shuffle the order of the teams
    our_index = random.randint(0, 1)
    enemy_index = 1 - our_index
    if our_index == 0:
        teams = [move, enemy_move]
    else:
        teams = [enemy_move, move]

    # fetch a random layout
    layout_name, layout_string = get_random_layout(filter='normal_without_dead_ends')
    parsed_layout = parse_layout(layout_string)

    # run a game
    game_state = run_game(teams, layout_dict=parsed_layout, max_rounds=300)

    # update the statistics
    if game_state['whowins'] == our_index:
        statistics['wins'] += 1
    elif game_state['whowins'] == enemy_index:
        statistics['losses'] += 1
    elif game_state['whowins'] == 2:
        statistics['draws'] += 1

print(f"We won {statistics['wins']} times, lost {statistics['losses']} times and drew {statistics['draws']} times.")
