"""
Generate maze layouts for 'pelita', without dead ends.

Algorithm:
* start with an empty grid
* draw a wall with gaps, dividing the grid in 2
* repeat recursively for each sub-grid
* find dead ends
* remove a wall at the dead ends

Players 1,3 always start in the bottom left; 2,4 in the top right
Food is placed randomly (though not too close to the pacmen starting positions)

Notes:
the final map includes a symmetric, flipped copy
the first wall has k gaps, the next wall has k/2 gaps, etc. (min=1)

Inspired by code by Dan Gillick
Completely rewritten by Pietro Berkes
Rewritten again (but not completely) by Tiziano Zito
"""

import numpy as np
import networkx as nx

from .base_utils import default_rng


north = (0, -1)
south = (0, 1)
east = (1, 0)
west = (-1, 0)


# character constants for walls, food, and empty spaces
W = b'#'
F = b'.'
E = b' '


def empty_maze(height, width):
    """Return an empty maze with external walls.

    A maze is a 2D array of characters representing walls, food, and agents.
    An empty maze is made of empty tiles, except for the external walls.
    """

    maze = np.empty((height, width), dtype='c')
    maze.fill(E)

    # add external walls
    maze[0, :].fill(W)
    maze[-1, :].fill(W)
    maze[:, 0].fill(W)
    maze[:, -1].fill(W)

    return maze


def maze_to_bytes(maze):
    """Return bytes representation of maze."""
    lines = [b''.join(maze[i,:])
             for i in range(maze.shape[0])]
    return b'\n'.join(lines)

def maze_to_str(maze):
    """Return a ascii-string representation of maze."""
    bytes_ = maze_to_bytes(maze)
    return bytes_.decode('ascii')

def bytes_to_maze(bytes_):
    """Return a maze numpy bytes array from a bytes representation."""
    rows = []
    for line in bytes_.splitlines():
        line = line.strip()
        if len(line) == 0:
            # skip empty lines
            continue
        cols = []
        for idx in range(len(line.strip())):
            # this crazyness is needed because bytes do not iterate like
            # strings: see the comments about iterating over bytes in
            # https://docs.python.org/3/library/stdtypes.html#bytes-objects
            cols.append(line[idx:idx+1])
        rows.append(cols)

    maze = np.array(rows, dtype=bytes)
    return maze

def str_to_maze(str_):
    """Return a maze numpy bytes array from a ascii string representation."""
    bytes_maze = str_.encode('ascii')
    return bytes_to_maze(bytes_maze)

def create_half_maze(maze, ngaps_center, rng=None):
    """Fill the left half of the maze with random walls.

    The second half can be created by mirroring the left part using
    the 'complete_maze' function.
    """
    rng = default_rng(rng)

    # first, we need a wall in the middle

    # the gaps in the central wall have to be chosen such that they can
    # be mirrored
    ch = maze.shape[0] - 2
    candidates = list(range(ch//2))
    rng.shuffle(candidates)
    half_gaps_pos = candidates[:ngaps_center // 2]
    gaps_pos = []
    for pos in half_gaps_pos:
        gaps_pos.append(pos)
        gaps_pos.append(ch - pos - 1)

    # make wall
    _add_wall_at(maze, (maze.shape[1] - 2) // 2 - 1, ngaps_center,
                 vertical=True, rng=rng, gaps_pos=gaps_pos)

    # then, fill the left half with walls
    _add_wall(maze[:, :maze.shape[1] // 2], ngaps_center // 2, vertical=False, rng=rng)

def _add_wall_at(maze, pos, ngaps, vertical, rng, gaps_pos=None):
    """
    add a wall with gaps

    maze -- maze where to place wall, plus a border of one element
    pos -- position where to put the wall within the center of the maze
           (border excluded)
    """

    if not vertical:
        maze = maze.T

    center = maze[1:-1, 1:-1]
    ch, cw = center.shape

    # place wall
    center[:, pos].fill(W)

    # place gaps
    ngaps = max(1, ngaps)
    # choose position of gaps if necessary
    if gaps_pos is None:
        # choose aandom positions
        gaps_pos = list(range(ch))
        rng.shuffle(gaps_pos)
        gaps_pos = gaps_pos[:ngaps]
        # do not block entrances
        if maze[0][pos + 1] == E:
            gaps_pos.insert(0, 0)
        if maze[-1][pos + 1] == E:
            gaps_pos.insert(0, ch - 1)
    for gp in gaps_pos:
        center[gp, pos] = E

    sub_mazes = [maze[:, :pos + 2], maze[:, pos + 1:]]

    if not vertical:
        sub_mazes = [sm.T for sm in sub_mazes]

    return sub_mazes

def _add_wall(maze, ngaps, vertical, rng):
    """Recursively build the walls of the maze.

    grid -- 2D array of characters representing the maze
    ngaps -- number of empty spaces to leave in the wall
    vertical -- if True, create a vertical wall, otherwise horizontal
    """

    h, w = maze.shape
    center = maze[1:-1, 1:-1]
    ch, cw = center.shape

    # no space for walls, interrupt recursion
    if ch < 3 and cw < 3:
        return

    size = cw if vertical else ch
    # create a wall only if there is some space in this direction
    min_size = rng.randint(3, 5)
    if size >= min_size:
        # place the wall at random spot
        pos = rng.randint(1, size-2)
        sub_mazes = _add_wall_at(maze, pos, ngaps, vertical, rng=rng)

        # recursively add walls
        for sub_maze in sub_mazes:
            _add_wall(sub_maze, max(1, ngaps // 2), not vertical, rng=rng)


def walls_to_graph(maze):
    """Transform a maze in a graph.

    The data on the nodes correspond to their coordinates, data on edges is
    the actions to take to transition to that edge.

    Returns:
    graph -- a Graph
    first_node -- the first node in the Graph
    """

    h, w = maze.shape
    directions = [west, east, north, south]

    graph = nx.Graph()
    # define nodes for maze
    for x in range(w):
        for y in range(h):
            if maze[y, x] != W:
                graph.add_node((x,y))
                # this is a free position, get its neighbors too
                for dx, dy in directions:
                    nbx, nby = (x+dx, y+dy)
                    # do not go out of bounds
                    try:
                        if maze[nby, nbx] == E:
                            graph.add_edge((x, y), (nbx, nby))
                    except IndexError:
                        # this move brought us out of the maze, just ignore it
                        continue
    return graph


def find_dead_ends(graph, width):
    """Find dead ends in a graph."""

    dead_ends = []
    for node in graph.nodes():
        if graph.degree(node) == 1 and node[0] < width-1:
            dead_ends.append(node)

    return dead_ends


def remove_dead_end(dead_node, maze):
    """Remove one dead end in a maze."""

    h, w = maze.shape

    # loop through the neighboring positions and remove the first wall we find
    # as long as it is not on the outer border or in the middle of the maze
    # not in the central wall x==w//2-1
    directions = (north, south, east, west)
    for direction in directions:
        nbx = dead_node[0]+direction[0]
        nby = dead_node[1]+direction[1]
        if nbx not in (0,w-1,w//2-1) and nby not in (0,h-1):
            neighbor = maze[nby, nbx]
            if neighbor == W:
                maze[nby, nbx] = E
                break


def remove_all_dead_ends(maze):
    height, width = maze.shape
    while True:
        maze_graph = walls_to_graph(maze)
        dead_ends = find_dead_ends(maze_graph, width)
        if len(dead_ends) == 0:
            break

        remove_dead_end(dead_ends[0], maze)

def find_chamber(graph):
    """Detect chambers (rooms with a single square entrance).

    Return (entrance, chamber), where `entrance` is the node representing the
    entrance to the chamber (None if no chamber is found), and `chamber` is the
    list of nodes within the chamber (empty list if no nodes are in the chamber).

    The entrance to a chamber is a node that when removed from the graph
    will result in the graph to be split into two disconnected graphs."""
    # minimum_node_cut returns a set of nodes of minimum cardinality that
    # disconnects the graph. This means that we have a chamber if the length
    # of this set is one, i.e. there is one node that when removed disconnects
    # the graph
    cuts = nx.minimum_node_cut(graph)
    if len(cuts) > 1:
        # no chambers, yeah!
        return None, []
    entrance = cuts.pop()
    # remove the cut, i.e. put a wall on the entrance
    lgraph = nx.restricted_view(graph, [entrance],[])
    # now get the resulting subgraphs
    subgraphs = sorted(nx.connected_components(lgraph), key=len)
    # let's get the smallest subgraph: this is going to be a chamber
    # (other subgraphs are other chambers (if any) and the 'rest' of the graph
    # return a list of nodes, instead of a set
    chamber = list(subgraphs[0])
    return entrance, chamber

def get_neighboring_walls(maze, locs):
    """Given a list of coordinates in the maze, return all neighboring walls.

    Walls on the outer border are ignored automatically."""
    height, width = maze.shape
    walls = []
    seen = []
    for nodex, nodey in locs:
        # if we are already on the border, skip this node
        if nodex<=0 or nodex>=(width-1) or nodey<=0 or nodey>=(height-1):
            continue
        # explore all directions around the current node
        for dirx, diry in (north, south, east, west):
            # get coordinates of neighbor in direction (dirx, diry)
            adjx, adjy = nodex+dirx, nodey+diry
            if (adjx, adjy) in seen:
                # we have visited this neighbor already
                continue
            else:
                seen.append((adjx, adjy))
            # check that we still are inside the maze
            if adjx<=0 or adjx>=(width-1) or adjy<=0 or adjy>=(height-1):
                # the neighbor is out of the maze
                continue
            if maze[adjy,adjx] == W:
                # this is a wall, store it
                walls.append((adjx, adjy))
    return walls

def remove_all_chambers(maze, rng=None):
    rng = default_rng(rng)

    maze_graph = walls_to_graph(maze)
    # this will find one of the chambers, if there is any
    entrance, chamber = find_chamber(maze_graph)
    while entrance is not None:
        # get all the walls around the chamber
        walls = get_neighboring_walls(maze, chamber)
        # choose a wall at random among the neighboring one and get rid of it
        bad_wall = rng.choice(walls)
        maze[bad_wall[1], bad_wall[0]] = E
        # we may have opened a door into this chamber, but there may be more
        # chambers to get rid of. Or, the wall we picked wasn't good enough and
        # didn't really open a new door to the chamber. I have no idea how to
        # distinguish this two cases. If we knew how to, we would spare quite
        # a few iterations here?
        # Well, as long as we keep on doing this we will eventually get rid
        # of all the chambers
        maze_graph = walls_to_graph(maze)
        entrance, chamber = find_chamber(maze_graph)


def add_food(maze, max_food, rng=None):
    """Add max_food pellets on the left side of the maze.

    We exclude the pacmen's starting positions and the central dividing border
    """
    rng = default_rng(rng)

    if max_food == 0:
        # no food needs to be added, return here
        return
    h, w = maze.shape
    pacmen = [(1,h-2), (1,h-3)]
    # get all free slots on the left side, excluding the dividing border
    free_y, free_x = np.where(maze[:,:w//2-1] == E)
    # convert it to a list of coordinate tuples
    free = list(zip(free_x, free_y))
    # remove the pacmen starting coordinates (we have to check that they are
    # indeed free before try to remove them
    [free.remove(pacman) for pacman in pacmen if pacman in free]
    # check if we have any free slots left
    if len(free) == 0 and max_food > 0:
        raise ValueError(f'No space left for food in maze')
    elif max_food > len(free):
        # check if we can indeed fit so much food in the maze
        raise ValueError(f'Can not fit {max_food} pellet in {len(free)} free slots')
    elif max_food < 0:
        raise ValueError(f'Can not add negative number of food ({max_food} given)')

    # now take max_food random positions out of this list
    food = rng.sample(free, max_food)
    # fit it in the maze
    for col, row in food:
        maze[row, col] = F

def add_pacmen(maze):
    ## starting pacmen positions
    maze[-2, 1] = b'b'
    maze[-3, 1] = b'a'
    maze[1, -2] = b'y'
    maze[2, -2] = b'x'

def get_new_maze(height, width, nfood, dead_ends=False, rng=None):
    """Create a new maze in text format.

    The maze is created with a recursive creation algorithm. The maze part of
    the blue team is a center-mirror version of the one for the red team.

    The function reserves space for 2 PacMan for each team in upper-right
    and lower-left corners of the maze. Food is added at random.

    Input arguments:
    height, width -- the size of the maze, including the outer walls
    nfood -- number of food dots for each team
    seed -- if not None, the random seed used to generate the maze
    dead_ends -- if True allow for dead ends and chambers in the maze

    A dead-end is a node with connectivity one.
    A chamber is a sub-graph such that there is a node in the sub-graph, the
    entrance to the chamber, that when removed from the graph will result in the
    graph to be split into two disconnected graphs.
    """
    if width%2 != 0:
        raise ValueError(f'Width must be even ({width} given)')

    rng = default_rng(rng)

    maze = empty_maze(height, width)
    create_half_maze(maze, height // 2, rng=rng)

    # make space for pacman (2 pacman each)
    maze[-2, 1] = E
    maze[-3, 1] = E

    # remove dead ends
    if not dead_ends:
        remove_all_dead_ends(maze)
        remove_all_chambers(maze, rng=rng)

    # add food
    add_food(maze, nfood, rng=rng)

    # complete right part of maze with mirror copy
    maze[:, width // 2:] = np.flipud(np.fliplr(maze[:, :width // 2]))

    # add pacman
    add_pacmen(maze)

    return maze_to_str(maze)
