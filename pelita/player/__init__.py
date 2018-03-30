
from .base import AbstractTeam, SimpleTeam, AbstractPlayer

from .base import (StoppingPlayer, SteppingPlayer, SpeakingPlayer,
                   RoundBasedPlayer, MoveExceptionPlayer, InitialExceptionPlayer,
                   DebuggablePlayer)

from .team import Team

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
