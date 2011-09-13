#!/bin/sh

SEED=39285
N=100

for COUNT in $(seq -w 1 $N);
do
   SEED=$(expr $SEED + 27)
   echo normal $COUNT
   ./create_maze.py --seed=$SEED --no-dead-ends --height=16 --width=32 > "normal_without_dead_ends_"$COUNT".layout"
   ./create_maze.py --seed=$SEED --dead-ends --height=16 --width=32 > "normal_with_dead_ends_"$COUNT".layout"
done

for COUNT in $(seq -w 1 $N);
do
   SEED=$(expr $SEED + 27)
   echo small $COUNT
   ./create_maze.py --seed=$SEED --no-dead-ends --food=10 --height=8 --width=18 > "small_without_dead_ends_"$COUNT".layout"
   ./create_maze.py --seed=$SEED --dead-ends --food=10 --height=8 --width=18 > "small_with_dead_ends_"$COUNT".layout"
done

for COUNT in $(seq -w 1 $N);
do
   SEED=$(expr $SEED + 27)
   echo big $COUNT
   ./create_maze.py --seed=$SEED --no-dead-ends --food=60 --height=32 --width=64 > "big_without_dead_ends_"$COUNT".layout"
   ./create_maze.py --seed=$SEED --dead-ends --food=60 --height=32 --width=64 > "big_with_dead_ends_"$COUNT".layout"
done
