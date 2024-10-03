#!/usr/bin/env bash
# initialize random seed, any subsequent evaluation of $RANDOM will get
# a different, but replicable random number
RANDOM=19155

# keep track of the seeds
SEEDF="_seeds_dead_ends"
echo > $SEEDF
echo "## pelita-createlayout --dead-ends -y 16 -x 32 -f 30 -s SEED > dead_ends_normal_XXX.layout" >> $SEEDF
echo "## pelita-createlayout --dead-ends -y 8 -x 16 -f 10 -s SEED > dead_ends_small_XXX.layout" >> $SEEDF
echo "## pelita-createlayout --dead-ends -y 32 -x 64 -f 60 -s SEED > dead_ends_big_XXX.layout" >> $SEEDF

# generate 1000 normal layouts
for COUNT in $(seq -w 0 999); do
    echo "Generating normal_$COUNT..."
    SEED=$RANDOM$RANDOM$RANDOM
    pelita-createlayout --dead-ends -y 16 -x 32 -f 30 -s $SEED > dead_ends_normal_${COUNT}.layout
    echo "dead_ends_normal_${COUNT} = $SEED" >> $SEEDF
done

# generate 100 small layouts
for COUNT in $(seq -w 0 99); do
    echo "Generating small_0$COUNT..."
    SEED=$RANDOM$RANDOM$RANDOM
    pelita-createlayout --dead-ends -y 8 -x 16 -f 10 -s $SEED > dead_ends_small_0${COUNT}.layout
    echo "dead_ends_small_0${COUNT} = $SEED" >> $SEEDF
done

# generate 100 big layouts
for COUNT in $(seq -w 0 99); do
    echo "Generating big_0$COUNT..."
    SEED=$RANDOM$RANDOM$RANDOM
    pelita-createlayout --dead-ends -y 32 -x 64 -f 60 -s $SEED > dead_ends_big_0${COUNT}.layout
    echo "dead_ends_big_0${COUNT} = $SEED" >> $SEEDF
done

