#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pelita.player import AbstractPlayer
from pelita.datamodel import stop

from .utils import utility

class MyPlayer(AbstractPlayer):
    """ Basically a clone of the StoppingPlayer. """

    def get_move(self):
        utility()
        return stop
