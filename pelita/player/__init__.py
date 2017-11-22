
from .base import AbstractPlayer
from .base2 import AbstractTeam, SimpleTeam, Player2

from .base2 import (StoppingPlayer, SteppingPlayer, SpeakingPlayer,
                    TurnBasedPlayer, MoveExceptionPlayer, InitialExceptionPlayer,
                    DebuggablePlayer)

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
    SmartRandomPlayer
]
