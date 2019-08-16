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

    # play each time on a different layout
    result = run_background_game(blue_move=blue, red_move=red)
    game['result'] = result

    # add to our collection of games
    collection.append(game)

# At the end we can picke the results to be analyzed later:
#import pickle
#with open('results.pic', 'wb') as fh:
    pickle.dump(collection, fh)
#
# - To open the pickle in another process:
#with open('results.pic', 'rb') as fh:
#    collection = pickle.load(fh)

# - If you want to replay a particular game, let's say the 10th game:
#replay = collection[10]

# - first check who was blue
#blue = replay['blue']
# - get the random seed for the game
#seed = replay['result']['seed']
# - let's assume that the attacker was blue, and the sed was 1234567,
#   then you can replay on the terminal with
# pelita --seed 1234567 demo04_basic_attacker.py demo05_basic_defender.py

# Here we only want to print some basic stats
attacker_wins = 0
defender_wins = 0
draws = 0
# this is attacker_score-defender_score
score_difference = 0

for i, game in enumerate(collection):
    blue = game['blue']
    result = game['result']
    if result['draw']:
        draws += 1
    elif blue == 'attacker':
        attacker_wins += result['blue_wins']
        defender_wins += result['red_wins']
        score_difference += result['blue_score'] - result['red_score']
    elif blue == 'defender':
        attacker_wins += result['red_wins']
        defender_wins += result['blue_wins']
        score_difference += result['red_score'] - result['blue_score']

print(f'Attacker wins: {attacker_wins}')
print(f'Defender wins: {defender_wins}')
print(f'Draws: {draws}')
print(f'Average score difference: {score_difference/(i+1)}')

