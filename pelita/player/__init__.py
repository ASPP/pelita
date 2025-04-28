# ruff: noqa: F401

from .base import (debuggable_player, move_exception_player,
                   round_based_player, speaking_player, stepping_player)
from .FoodEatingPlayer import food_eating_player
from .RandomExplorerPlayer import random_explorer_player
from .RandomPlayers import nq_random_player, random_player
from .SmartEatingPlayer import smart_eating_player
from .SmartRandomPlayer import smart_random_player
from .StoppingPlayer import stopping_player

SANE_PLAYERS = [
    random_player,
    nq_random_player,
    food_eating_player,
    smart_eating_player,
    random_explorer_player,
    smart_random_player]
