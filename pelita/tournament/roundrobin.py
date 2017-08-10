#!/usr/bin/env python3

import itertools
import random

def initial_state(teams):
    rr = []
    for pair in itertools.combinations(teams, 2):
        match = list(pair)
        random.shuffle(match)
        rr.append(tuple(match))
    # shuffle the matches for more fun
    random.shuffle(rr)
    return rr

# def round_robin(state, teams):
#    if not state:
#        state = initial_state

