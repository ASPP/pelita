#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pelita.player import AbstractPlayer, Squad
from pelita.datamodel import stop


class MyPlayer(AbstractPlayer):
    """ Basically a clone of the StoppingPlayer. """

    def get_move(self):
        return stop

def factory():
    return Squad("My Team", MyPlayer(), MyPlayer())

