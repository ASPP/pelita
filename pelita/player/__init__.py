
from .base import AbstractTeam, SimpleTeam, AbstractPlayer

from .base import (stepping_player, speaking_player,
                   round_based_player, move_exception_player,
                   debuggable_player)

from .team import Team

from .RandomPlayers import RandomPlayer, NQRandomPlayer
from .FoodEatingPlayer import FoodEatingPlayer
from .SmartEatingPlayer import SmartEatingPlayer
from .RandomExplorerPlayer import RandomExplorerPlayer
from .SmartRandomPlayer import SmartRandomPlayer
from .StoppingPlayer import StoppingPlayer

SANE_PLAYERS = [
    RandomPlayer,
    NQRandomPlayer,
    FoodEatingPlayer,
    SmartEatingPlayer,
    RandomExplorerPlayer,
    SmartRandomPlayer]
