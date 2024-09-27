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
DEAD_ENDS = False
CHAMBERS = False

description="""
Return a new random layout to be used by pelita
"""
epilog=f"""
NOTE: To re-create the layouts used in the installed pelita, you can use the
following shell script:

# initialize random seed, any subsequent evaluation of $RANDOM will get
# a different, but replicable random number
RANDOM=39285

# keep track of the seeds
SEEDF="_seeds"
echo > $SEEDF
echo "## pelita-createlayout -y {HEIGHT} -x {WIDTH} -f {FOOD} -s SEED > normal_XXX.layout" >> $SEEDF
echo "## pelita-createlayout -y {HEIGHT//2} -x {WIDTH//2} -f {FOOD//3} -s SEED > small_XXX.layout" >> $SEEDF
echo "## pelita-createlayout -y {HEIGHT*2} -x {WIDTH*2} -f {FOOD*2} -s SEED > big_XXX.layout" >> $SEEDF

# generate 1000 normal layouts
for COUNT in $(seq -w 0 999); do
    echo "Generating normal_$COUNT..."
    SEED=$RANDOM$RANDOM$RANDOM
    pelita-createlayout -y {HEIGHT} -x {WIDTH} -f {FOOD} -s $SEED > normal_${{COUNT}}.layout
    echo "normal_${{COUNT}} = $SEED" >> $SEEDF
done

# generate 100 small layouts
for COUNT in $(seq -w 0 99); do
    echo "Generating small_0$COUNT..."
    SEED=$RANDOM$RANDOM$RANDOM
    pelita-createlayout -y {HEIGHT//2} -x {WIDTH//2} -f {FOOD//3} -s $SEED > small_0${{COUNT}}.layout
    echo "small_0${{COUNT}} = $SEED" >> $SEEDF
done

# generate 100 big layouts
for COUNT in $(seq -w 0 99); do
    echo "Generating big_0$COUNT..."
    SEED=$RANDOM$RANDOM$RANDOM
    pelita-createlayout -y {HEIGHT*2} -x {WIDTH*2} -f {FOOD*2} -s $SEED > big_0${{COUNT}}.layout
    echo "big_0${{COUNT}} = $SEED" >> $SEEDF
done
"""

def default(text, default):
    return text + f' (default: {default})'

def main():
    parser = argparse.ArgumentParser(
                  description=description,
                  epilog=epilog,
                  formatter_class=argparse.RawDescriptionHelpFormatter,
                  add_help=True)

    parser.add_argument('--height', '-y', default=HEIGHT, type=int, metavar='Y',
                        help=default('height of the maze', HEIGHT))
    parser.add_argument('--width', '-x', default=WIDTH, type=int, metavar='X',
                        help=default('width of the maze', WIDTH))
    parser.add_argument('--food', '-f', default=FOOD, type=int, metavar='F',
                        help=default('food pellets for each team', FOOD))
    parser.add_argument('--seed', '-s', default=SEED, type=int, metavar='S',
                        help=default('random seed', SEED))
    parser.add_argument('--dead-ends', '-d', const=True, action='store_const',
                        help=default('allow for dead ends and chambers in the maze',
                                     DEAD_ENDS))

    args = parser.parse_args()

    maze_str = get_new_maze(args.height, args.width, nfood=args.food,
                            seed=args.seed, dead_ends=args.dead_ends)

    sys.stdout.write(maze_str+'\n')
    sys.stdout.close()

if __name__ == "__main__":
    main()
