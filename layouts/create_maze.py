#!/usr/bin/env python3
"""Python script to generate a new maze.

The maze will be sent to sys.out .
"""

import sys
import optparse
from .maze_generator import get_new_maze


def default(str):
    return str + ' [Default: %default]'


def main(argv):
    parser = optparse.OptionParser()

    parser.add_option("-y", "--height", type="int", default=16,
                      help=default("height of the maze"))
    parser.add_option("-x", "--width", type="int", default=32,
                      help=default("width of the maze"))

    parser.add_option("-f", "--food", type="int", default=30,
                      help=default("number of food dots for each team"))

    parser.add_option("--seed", type="int", default=None,
                      help="fix the random seed used to generate the maze")
    parser.add_option("--dead-ends", action="store_true", dest="dead_ends",
                      default=False,
                      help="allow dead ends in the maze")
    parser.add_option("--no-dead-ends", action="store_false", dest="dead_ends",
                      help="do not allow dead ends in the maze [Default]")

    opts, args = parser.parse_args()
    sys.stdout.buffer.write(get_new_maze(opts.height, opts.width, nfood=opts.food,
                            seed=opts.seed, dead_ends=opts.dead_ends))


if __name__ == "__main__":
    main(sys.argv[1:])
