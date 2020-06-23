#!/usr/bin/env python3

import argparse
import timeit

from pelita.layout import parse_layout
from pelita.game import run_game
from pelita.player import stopping_player, nq_random_player

LAYOUT="""
##################################
#...   #      .#     #  #       y#
# ## #   # ###    #  #     #####x#
#.   # #    # .   # ##           #
#.#    #  .    #    .  # #########
# ## # ## ####    # ##.   . .   .#
#.. .  .  #. . #. #  # ## #####  #
# ## #### #.## #     #  .  . . ..#
#..  ..   # #  #  #    ##### #####
##### #####    #  #  # #   ..  ..#
#.. . .  .  #     # ##.# #### ## #
#  ##### ## #  # .# . .#  .  . ..#
#.   . .   .## #    #### ## # ## #
######### #  .    #    .  #    #.#
#           ## #   . #    # #   .#
#a#####     #  #    ### #   # ## #
#b       #  #     #.      #   ...#
##################################
"""

layout = parse_layout(LAYOUT)

def run_stopping():
    return run_game([stopping_player, stopping_player], max_rounds=300, layout_dict=layout, print_result=False, allow_exceptions=True)

def run_nqrandom():
    return run_game([nq_random_player, nq_random_player], max_rounds=300, layout_dict=layout, print_result=False, allow_exceptions=True)

def run_stopping_remote():
    return run_game(["pelita/player/StoppingPlayer.py", "pelita/player/StoppingPlayer.py"], max_rounds=300, layout_dict=layout, print_result=False, allow_exceptions=True)

def run_nqrandom_remote():
    return run_game(["pelita/player/RandomPlayers.py", "pelita/player/RandomPlayers.py"], max_rounds=300, layout_dict=layout, print_result=False, allow_exceptions=True)

def parse_args():
    parser = argparse.ArgumentParser(description='Benchmark pelita run_game')
    parser.add_argument('--repeat', help="Number of repeats of timeit.", default=5, type=int)
    parser.add_argument('--number', help="Number of iterations inside timeit.", default=10, type=int)

    return parser.parse_args()

if __name__ == '__main__':
    args = parse_args()
    REPEAT = args.repeat
    NUMBER = args.number

    print(f"Running {NUMBER} times. Fastest out of {REPEAT}:")
    tests = [
        ("Stopping", run_stopping),
        ("NQ_Random", run_nqrandom),
        ("Stopping (remote)", run_stopping_remote),
        ("NQ_Random (remote)", run_nqrandom_remote),
    ]
    for name, fn in tests:
        result = min(timeit.repeat(fn, repeat=REPEAT, number=NUMBER))
        print(f"{name:<20}: {result}")

    #import cProfile
    #cProfile.runctx("""run()""", globals(), locals())
