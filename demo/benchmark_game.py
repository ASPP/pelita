#!/usr/bin/env python3

import argparse
import functools
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

def run(teams, max_rounds):
    return run_game(teams, max_rounds=max_rounds, layout_dict=layout, print_result=False, allow_exceptions=True)

def parse_args():
    parser = argparse.ArgumentParser(description='Benchmark pelita run_game')
    parser.add_argument('--repeat', help="Number of repeats of timeit.", default=5, type=int)
    parser.add_argument('--number', help="Number of iterations inside timeit.", default=10, type=int)
    parser.add_argument('--max-rounds', help="Max rounds.", default=300, type=int)

    return parser.parse_args()

if __name__ == '__main__':
    args = parse_args()
    REPEAT = args.repeat
    NUMBER = args.number
    MAX_ROUNDS = args.max_rounds

    print(f"Running {NUMBER} times with max {MAX_ROUNDS} rounds. Fastest out of {REPEAT}:")
    tests = [
        ("Stopping", [stopping_player, stopping_player]),
        ("NQ_Random", [nq_random_player, nq_random_player]),
        ("Stopping (remote)", ["pelita/player/StoppingPlayer.py", "pelita/player/StoppingPlayer.py"]),
        ("NQ_Random (remote)", ["pelita/player/RandomPlayers.py", "pelita/player/RandomPlayers.py"]),
    ]
    for name, teams in tests:
        result = min(timeit.repeat(functools.partial(run, teams=teams, max_rounds=MAX_ROUNDS), repeat=REPEAT, number=NUMBER))
        print(f"{name:<20}: {result}")

    #import cProfile
    #cProfile.runctx("""run()""", globals(), locals())
