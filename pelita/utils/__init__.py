import random

from ..player.team import create_layout, Game, bots_from_layout

def setup_test_game(*, layout, game=None, is_blue=True, rounds=None, score=None, seed=None):
    if game is not None:
        raise RuntimeError("Re-using an old game is not implemented yet.")

    if isinstance(layout, str):
        layout = create_layout(layout)

#    elif not isinstance(layout, Layout):
#        raise TypeError("layout needs to be of type Layout or str.")

    rng = [random.Random(seed) for _ in range(4)]
    if score is None:
        score = [0, 0]
    bots = bots_from_layout(layout, is_blue, score, rng, round)
  
    if is_blue:
        team = [bots[0], bots[2]]
    else:
        team = [bots[1], bots[3]]

    storage = {}
    game = Game(team, storage)
    return game 
