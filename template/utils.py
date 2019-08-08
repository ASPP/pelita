import networkx


def walls_to_graph(walls):
    """Return a networkx Graph object given the walls"""
    graph = networkx.Graph()
    width = max([coord[0] for coord in walls]) + 1
    heigth = max([coord[1] for coord in walls]) + 1
    for x in range(width):
        for y in range(heigth):
            if (x, y) not in walls:
                # this is a free position, get its neighbors
                for delta_x, delta_y in ((1,0), (-1,0), (0,1), (0,-1)):
                    neighbor = (x + delta_x, y + delta_y)
                    # we don't need to check for getting neighbors out of the maze
                    # because our mazes are all surrounded by walls, i.e. our
                    # deltas will not put us out of the maze
                    if neighbor not in walls:
                        # this is a genuine neighbor, add an edge in the graph
                        graph.add_edge((x, y), neighbor)
    return graph


import numpy as np

def draw_coords(coords, ax, params={}):
    """
    Takes a list of coordinates and

    Input:
    - coords: list of tuples of x,y coordinates
    - ax: a pyplot ax object
    - params: parameters to be passed to the scatter function (e.g. shape, size, color, etc.)
    """
    if type(coords)!=list:
        coords_x, coords_y = coords
    else:
        # get seperate lists of x and y coordinates from a list of tuples
        coords_x, coords_y = zip(*coords)
    ax.scatter(coords_x, coords_y, **params)
    return ax

def replace_coords_in_matrix(mat, coords, val):
    """
    Computes a numpy array which takes the value val
    Input:
    - mat: numpy array
    - coords: list of tuples of x,y coordinates
    - val: value to write into the appropriate fields
    Returns:
    - mat: numpy array
    """
    # get seperate lists of x and y coordinates from a list of tuples
    coords_x, coords_y = zip(*coords)
    # matrices have y,x indexing!
    mat[coords_y, coords_x] = val
    return(mat)

def make_wall_matrix(bot):
    """
    Computes a numpy array which takes the value 1 at coordinates that have a wall and zero everywhere else
    Input:
    - bot: pelita bot object
    Returns:
    - mat: numpy array
    """
    maze_width = max([x for x, y in bot.walls])+1
    maze_height = max([y for x, y in bot.walls])+1
    mat = np.zeros((maze_height, maze_width))
    # get seperate lists of x and y coordinates from a list of tuples
    wall_x, wall_y = zip(*bot.walls)
    # matrices have y,x indexing!
    mat[wall_y, wall_x] = 1
    return mat

def draw_game_elements(bot, ax):
    """
    draws game state as scatter elements given a bot object.

    Input:
    - bot : pelita bot object
    - ax : a pyplot axis object
    Returns:
    -ax : a pyplot axis object
    """
    # Depending which team we are, we need to color the board appropriately
    if bot.is_blue:
        col_home_food = "blue"
        col_home_b1 = "green"
        col_home_b2 = "darkgreen"
        col_enemy_food = "red"
        col_enemy_b1 = "orange"
        col_enemy_b2 = "darkred"
    else:
        col_home_food = "red"
        col_home_b1 = "orange"
        col_home_b2 = "darkred"
        col_enemy_food = "blue"
        col_enemy_b1 = "green"
        col_enemy_b2 = "darkgreen"

    # Then we call the draw_coords function for each type of element we want to draw.
    # Each can be customized with whichever color, shape and size you want.
    ax = draw_coords(bot.position, ax, {"c": col_home_b1, "marker": "*"})
    ax = draw_coords(bot.walls, ax, {"c": "black", "marker": "s", "s": 20})
    ax = draw_coords(bot.other.position, ax, {"c": col_home_b2, "marker": "*"})
    ax = draw_coords(bot.food, ax, {"c": col_home_food, "s": 9})
    ax = draw_coords(bot.enemy[0].food, ax, {"c": col_enemy_food, "s": 1})
    ax = draw_coords(bot.enemy[0].position, ax, {"c": col_enemy_b1, "marker": "*"})
    ax = draw_coords(bot.enemy[1].position, ax, {"c": col_enemy_b2, "marker": "*"})
    ax.axvline(np.sum(ax.get_xlim()) / 2, c="black")
    # This is to get the coordinate system to have it's origin in the top left
    yd, yu = ax.get_ylim()
    if yd < yu:
        ax.invert_yaxis()
    return ax
