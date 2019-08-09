#!/usr/bin/env python3
"""Python script to generate a new maze.

The maze will be sent to sys.out .
"""

import sys
import argparse

from pelita.maze_generator import get_new_maze

HEIGHT = 16
WIDTH = 32
FOOD = 30
SEED = None

def default(text, default):
    return text + f' (default: {default})'



def main():
    parser = argparse.ArgumentParser(
                  description='Return a new random layout to be used by pelita',
                  add_help=True)

    parser.add_argument('--height', '-y', default=HEIGHT, type=int, metavar='Y',
                        help=default('height of the maze', HEIGHT))
    parser.add_argument('--width', '-x', default=WIDTH, type=int, metavar='X',
                        help=default('width of the maze', WIDTH))
    parser.add_argument('--food', '-f', default=FOOD, type=int, metavar='F',
                        help=default('food pellets for each team', FOOD))
    parser.add_argument('--seed', '-s', default=SEED, type=int, metavar='S',
                        help=default('random seed', SEED))

    args = parser.parse_args()

    maze_str = get_new_maze(args.height, args.width, nfood=args.food,
                            seed=args.seed)

    sys.stdout.write(maze_str+'\n')
    sys.stdout.close()

if __name__ == "__main__":
    main()
