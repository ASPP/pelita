#!/usr/bin/env bash
# initialize random seed, any subsequent evaluation of $RANDOM will get
# a different, but replicable random number
RANDOM=39285

# keep track of the seeds
SEEDF="_seeds"
echo > $SEEDF
echo "## pelita-createlayout -y 16 -x 32 -f 30 -s SEED > normal_XXX.layout" >> $SEEDF
echo "## pelita-createlayout -y 8 -x 16 -f 10 -s SEED > small_XXX.layout" >> $SEEDF
echo "## pelita-createlayout -y 32 -x 64 -f 60 -s SEED > big_XXX.layout" >> $SEEDF

# generate 1000 normal layouts
for COUNT in $(seq -w 0 999); do
    echo "Generating normal_$COUNT..."
    SEED=$RANDOM$RANDOM$RANDOM
    pelita-createlayout -y 16 -x 32 -f 30 -s $SEED > normal_${COUNT}.layout
    echo "normal_${COUNT} = $SEED" >> $SEEDF
done

# generate 100 small layouts
for COUNT in $(seq -w 0 99); do
    echo "Generating small_0$COUNT..."
    SEED=$RANDOM$RANDOM$RANDOM
    pelita-createlayout -y 8 -x 16 -f 10 -s $SEED > small_0${COUNT}.layout
    echo "small_0${COUNT} = $SEED" >> $SEEDF
done

# generate 100 big layouts
for COUNT in $(seq -w 0 99); do
    echo "Generating big_0$COUNT..."
    SEED=$RANDOM$RANDOM$RANDOM
    pelita-createlayout -y 32 -x 64 -f 60 -s $SEED > big_0${COUNT}.layout
    echo "big_0${COUNT} = $SEED" >> $SEEDF
done

