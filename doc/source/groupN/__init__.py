#!/usr/bin/env python3

from pelita.player import SimpleTeam
from .my_player import MyPlayer

# The default factory method, which this module must export.
# It must return an instance of `SimpleTeam`  containing
# the name of the team and the respective instances for
# the first and second player.

def team():
    return SimpleTeam("My Team", MyPlayer(), MyPlayer())

# For testing purposes, one may use alternate team factory methods::
#
#     def test_team():
#          return SimpleTeam("Our alternate Team", AlternatePlayer(), AlternatePlayer())
#
# To be used as follows::
#
#     $ pelita path_to/groupN/:test_team
