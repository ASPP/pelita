
from .base import (stepping_player, speaking_player,
                   round_based_player, move_exception_player,
                   debuggable_player)


from .RandomPlayers import random_player, nq_random_player
from .FoodEatingPlayer import food_eating_player
from .SmartEatingPlayer import smart_eating_player
from .RandomExplorerPlayer import random_explorer_player
from .SmartRandomPlayer import smart_random_player
from .StoppingPlayer import stopping_player

SANE_PLAYERS = [
    random_player,
    nq_random_player,
    food_eating_player,
    smart_eating_player,
    random_explorer_player,
    smart_random_player]
