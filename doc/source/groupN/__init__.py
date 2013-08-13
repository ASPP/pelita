#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pelita.player import Squad
from .my_player import MyPlayer

# The default factory method, which this module must export.
# It must return an instance of `Squad`  containing
# the name of the team and the respective instances for
# the first and second player.

def factory():
    return Squad("My Team", MyPlayer(), MyPlayer())

# For testing purposes, one may use alternate factory methods::
#
#     def alternate_factory():
#          return Squad("Our alternate Team", AlternatePlayer(), AlternatePlayer())
#
# To be used as follows::
#
#     $ ./pelitagame path_to/groupN/:alternate_factory

