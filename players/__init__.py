
from .RandomPlayers import RandomPlayer, NQRandomPlayer
from .FoodEatingPlayer import FoodEatingPlayer
from .SmartEatingPlayer import SmartEatingPlayer
from .RandomExplorerPlayer import RandomExplorerPlayer
from .SmartRandomPlayer import SmartRandomPlayer

SANE_PLAYERS = [
    RandomPlayer,
    NQRandomPlayer,
    FoodEatingPlayer,
    SmartEatingPlayer,
    RandomExplorerPlayer,
    SmartRandomPlayer]

__ALL__ = list(SANE_PLAYERS)

