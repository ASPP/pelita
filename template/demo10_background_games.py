# Run this script with
#
# python3 demo10_background_games.py
#
# - Run 100 games in the background to gather statistics
# - We'll use a team of basic defenders against a team of basic attackers
import random

from pelita.utils import run_background_game

from demo05_basic_defender import move as move_defender
from demo04_basic_attacker import move as move_attacker

NUM_GAMES = 100

statistics = {'defender_wins': 0, 'attacker_wins': 0, 'draws': 0}

# fix the seed to get replicable games
seed = random.seed(42)

collection = []

for idx in range(NUM_GAMES):

    # dictionary to store game parameters
    game = {}

    # play with the defenders and attackers as blue and red team alternatively
    if idx%2 == 0:
        blue = move_defender
        red = move_attacker
        game['blue'] = 'defender'
    else:
        blue = move_attacker
        red = move_defender
        game['blue'] = 'attacker'

    # get a seed for this game, so that we can replicate it later
    game_seed = random.randint(1, 2**31)
    game['seed'] = game_seed

    # play each time on a different layout
    game_state = run_background_game(blue_move=blue, red_move=red, seed=game_seed)
    game['state'] = game_state

    # add to our collection of games
    collection.append(game)

# at the end we can picke the results to be analyzed later
#import pickle
#with open('results.pic', 'wb') as fh:
#    pickle.dump(collection, fh)
#
# to open the pickle in another process
#with open('results.pic', 'rb') as fh:
#    collection = pickle.load(fh)

# Here we only want to print some basic stats
attacker_wins = 0
defender_wins = 0
draws = 0
# this is attacker_score-defender_score
score_difference = 0

for i, game in enumerate(collection):
    blue = game['blue']
    game_state = game['state']
    if game_state['draw']:
        draws += 1
    elif blue == 'attacker':
        attacker_wins += game_state['blue_wins']
        defender_wins += game_state['red_wins']
        score_difference += game_state['blue_score'] - game_state['red_score']
    elif blue == 'defender':
        attacker_wins += game_state['red_wins']
        defender_wins += game_state['blue_wins']
        score_difference += game_state['red_score'] - game_state['blue_score']

print(f'Attacker wins: {attacker_wins}')
print(f'Defender wins: {defender_wins}')
print(f'Draws: {draws}')
print(f'Average score difference: {score_difference/(i+1)}')

