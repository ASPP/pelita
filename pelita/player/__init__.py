
from .base import AbstractTeam, SimpleTeam, AbstractPlayer

from .base import (stepping_player, speaking_player,
                   round_based_player, move_exception_player,
                   debuggable_player)

from .team import Team

from .RandomPlayers import random_player, nq_random_player
from .FoodEatingPlayer import FoodEatingPlayer
from .SmartEatingPlayer import smart_eating_player
from .RandomExplorerPlayer import RandomExplorerPlayer
from .SmartRandomPlayer import SmartRandomPlayer
from .StoppingPlayer import stopping_player

SANE_PLAYERS = [
    random_player,
    nq_random_player,
    FoodEatingPlayer,
    smart_eating_player,
    RandomExplorerPlayer,
    SmartRandomPlayer]
