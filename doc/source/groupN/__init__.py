#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pelita.player import SimpleTeam
from .my_player import MyPlayer

def factory():
    return SimpleTeam("My Team", MyPlayer(), MyPlayer())
