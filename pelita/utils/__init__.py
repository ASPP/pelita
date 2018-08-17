from ..game_master import GameMaster
from ..containers import Mesh
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

def create_newstyle_layout(*layouts, food=None, teams=None, enemies=None):
    meshes = [
        load_layout(layout_str)
        for layout_str in layouts
    ]
    merged = merge_meshes(*meshes)
    # Add additional food:
    for f in food:
        if '.' not in merged[f]:
            merged[f] += '.'
    # Add additional teams:
    if teams is not None:
        idx_team1, idx_team2 = teams
        if idx_team1 is not None:
            if '1' not in merged[idx_team1]:
                merged[idx_team1] += '1'
        if idx_team2 is not None:
            if '2' not in merged[idx_team2]:
                merged[idx_team2] += '2'
    if enemies is not None:
        idx_team1, idx_team2 = teams
        if idx_team1 is not None:
            if 'E' not in merged[idx_team1]:
                merged[idx_team1] += 'E'
        if idx_team2 is not None:
            if 'E' not in merged[idx_team2]:
                merged[idx_team2] += 'E'
    

 
def load_layout(layout_str):
    build = []
    width = None
    height = None
    for row in layout_str.splitlines():
        stripped = row.strip()
        if not stripped:
            continue
        if width is not None:
            if len(stripped) != width:
                raise ValueError("Layout has differing widths.")
        width = len(stripped)
        build.append(stripped)

    height = len(build)
    mesh = Mesh(width, height, data=list("".join(build)))
    # Check that the layout is surrounded with walls
    for i in range(width):
        if not (mesh[i, 0] == mesh[i, height - 1] == '#'):
            raise ValueError("Layout not surrounded with #.")
    for j in range(height):
        if not (mesh[0, j] == mesh[width - 1, j] == '#'):
            raise ValueError("Layout not surrounded with #.")
    return mesh

def merge_meshes(*meshes):
    # start from the first mesh
    mesh = meshes[0]
    # now add the rest

    for m in meshes[1:]:
        # check that all meshes have the same width and height
        if not mesh.width == m.width:
            raise ValueError("Meshes have not the same width.")
        if not mesh.height == m.height:
            raise ValueError("Meshes have not the same height.")
        
        for idx, items in m.items():
            # If we find a wall that is not in the original, it is an error
            # Vice versa, if we have a wall in the old meshes, we need to find
            # a wall in the new meshes as well
            if ('#' in items and '#' not in mesh[idx]) or \
               ('#' in mesh[idx] and not '#' in items):
                raise ValueError("Found wall that was not in all meshes.")
            
            # We collect all the food we can find:
            if '.' in items and not '.' in mesh[idx]:
                mesh[idx] += '.'
            # We collect all bots we can find:
            for bot in ['1', '2', 'E']:
                if bot in items and not bot in mesh[idx]:
                    mesh[idx] += bot

    return mesh