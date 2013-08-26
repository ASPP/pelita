
from .RandomPlayers import RandomPlayer, NQRandomPlayer
from .BasicDefensePlayer import BasicDefensePlayer
from .BFSPlayer import BFSPlayer
from .FoodEatingPlayer import FoodEatingPlayer
from .RandomExplorerPlayer import RandomExplorerPlayer
from .SmartRandomPlayer import SmartRandomPlayer

SANE_PLAYERS = [
    RandomPlayer,
    NQRandomPlayer,
    BasicDefensePlayer,
    BFSPlayer,
    FoodEatingPlayer,
    RandomExplorerPlayer,
    SmartRandomPlayer]
