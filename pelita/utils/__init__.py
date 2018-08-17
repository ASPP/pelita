from ..game_master import GameMaster
from ..player.team import Team

class PlaceholderTeam:
    def __init__(self):
        pass

def stopping(turn, game):
    return (0, 0)

def setup_test_game(layout, game=None, is_left=True, rounds=None, score=None, seed=None):

    teams = [
        Team(stopping),
        Team(stopping)
    ]
    gm = GameMaster(layout, teams, 4, 1)
    gm.set_initial()
    gm.play_step()
    universe = gm.universe
    print(universe)

    return gm.player_teams[not is_left]._team_game


    layout = """
    ########
    #E ###.#
    #1.  0A#
    ########
    A: E.
    """

