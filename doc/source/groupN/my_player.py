#!/usr/bin/env python3

from pelita.player import AbstractPlayer
from pelita.datamodel import stop

# use relative imports for things inside your module
from .utils import utility

class MyPlayer(AbstractPlayer):
    """ Basically a clone of the StoppingPlayer. """

    def get_move(self):
        utility()
        return stop
