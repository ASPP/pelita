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
"""
import random
import sys

import numpy
import networkx as nx


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

    maze = numpy.empty((height, width), dtype='c')
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

    maze = numpy.array(rows, dtype=bytes)
    return maze

def str_to_maze(str_):
    """Return a maze numpy bytes array from a ascii string representation."""
    bytes_maze = str_.encode('ascii')
    return bytes_to_maze(bytes_maze)

def create_half_maze(maze, ngaps_center):
    """Fill the left half of the maze with random walls.

    The second half can be created by mirroring the left part using
    the 'complete_maze' function.
    """

    # first, we need a wall in the middle

    # the gaps in the central wall have to be chosen such that they can
    # be mirrored
    ch = maze.shape[0] - 2
    candidates = list(range(ch//2))
    random.shuffle(candidates)
    half_gaps_pos = candidates[:ngaps_center // 2]
    gaps_pos = []
    for pos in half_gaps_pos:
        gaps_pos.append(pos)
        gaps_pos.append(ch - pos - 1)

    # make wall
    _add_wall_at(maze, (maze.shape[1] - 2) // 2 - 1, ngaps_center,
                 vertical=True, gaps_pos=gaps_pos)

    # then, fill the left half with walls
    _add_wall(maze[:, :maze.shape[1] // 2], ngaps_center // 2, vertical=False)

def _add_wall_at(maze, pos, ngaps, vertical, gaps_pos=None):
    """
    add a wall with gaps

    maze -- maze where to place wall, plus a border of one element
    pos -- position where to put the wall whithin the center of the maze
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
        random.shuffle(gaps_pos)
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

def _add_wall(maze, ngaps, vertical):
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
    min_size = random.randint(3, 5)
    if size >= min_size:
        # place the wall at random spot
        pos = random.randint(1, size-2)
        sub_mazes = _add_wall_at(maze, pos, ngaps, vertical)

        # recursively add walls
        for sub_maze in sub_mazes:
            _add_wall(sub_maze, max(1, ngaps // 2), not vertical)


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


def remove_dead_end(dead_node, maze_graph, maze):
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

        remove_dead_end(dead_ends[0], maze_graph, maze)

def get_connectivity(maze, maze_graph=None):
    if maze_graph is None:
        maze_graph,_ = walls_to_graph(maze, class_=nx.Graph)
    return nx.node_connectivity(maze_graph)

def open_door_into_chamber(maze, chamber):
    height, width = maze.shape
    # look for the first wall around the chamber which is not on the
    # outer border or on the dividing border
    done = False
    for nodex, nodey in chamber:
        for dirx, diry in (north, south, east, west):
            # make a local copy of the maze to be modified for tests
            #lmaze = maze.copy()
            # get coordinates of neighbor in direction (dirx, diry)
            adjx, adjy = nodex+dirx, nodey+diry
            # check that we still are inside the maze and not on the
            # dividing border between the two homezones
            if adjx<=0 or adjx>=(width//2-1) or adjy<=0 or adjy>=(height-1):
                # we can skip this neighbor
                continue
            # first condition, the neighbor is a wall
            is_wall = (maze[adjy,adjx] == W)
            if is_wall:
                maze[adjy, adjx] = E
                # fix also the center mirrored element
                maze[height-adjy-1, width-adjx-1] = E
                done = True
                break
        if done:
            break


def remove_all_chambers(maze):
    height, width = maze.shape
    maze_graph,_ = walls_to_graph(maze, class_=nx.Graph)
    # when the connectivity of the graph is 1, there is one node that when
    # removed splits the graph in two. The node is the entrance to a chamber
    connectivity = get_connectivity(maze, maze_graph)
    while connectivity < 2:
        # There are chambers
        # loop through all nodes to find out where the chambers are
        chambers = []
        for node in maze_graph:
            # only detect in the left half of the maze, we know the maze is symmetric
            if node[0] >= (width//2-1):
                continue
            # make a local copy of the graph
            G = maze_graph.copy()
            # remove the current node and check if we split the graph in two
            G.remove_node(node)
            # sort the subgraphs by length, shortest first
            subgraphs = sorted(nx.connected_components(G), key=len)
            if len(subgraphs) == 1:
                # the graph wasn't split, skip this node
                continue
            else:
                # loop through the subgraphs, irgnoring the biggest one, which
                # is the "rest" after the split of the chambers
                for subgraph in subgraphs[:-1]:
                    chamber = subgraph
                    # if the subgraph has more than one node, we have detected
                    # a chamber
                    if len(chamber) > 1:
                        chambers.append(chamber)
        # loop through all possible pairs of chambers, and only retain those
        # who are not subset of others
        dupes = []
        for idx1, ch1 in enumerate(chambers):
            for idx2 in range(idx1+1, len(chambers)):
                ch2 = chambers[idx2]
                if ch1 in dupes or ch2 in dupes:
                    continue
                if ch1 < ch2:
                    dupes.append(ch1)
                elif ch2 < ch1:
                    dupes.append(ch2)

        for dupe in dupes:
            chambers.remove(dupe)

        # now that we have a list of the chambers, let's care only about those
        # that contain food
        food_chambers = []
        for chamber in chambers:
            with_food = False
            for node in chamber:
                if maze[node[1], node[0]] == F:
                    with_food = True
            if with_food:
                food_chambers.append(chamber)

        # for each food chamber, open a door to the chamber by
        # piercing a hole into one of the walls around the chamber
        for chamber in food_chambers:
            open_door_into_chamber(maze, chamber)

        # now that are no chambers with food anymore,
        # let's spin again in case there were some chambers contained into other
        # chambers
        # - get a new graph and calculate new connectivity
        maze_graph,_ = walls_to_graph(maze, class_=nx.Graph)
        connectivity = get_connectivity(maze, maze_graph)
        # even if connectivity is 1, if we don't have any food chambers we can stop
        if connectivity < 2 and len(food_chambers) == 0:
            connectivity = 2

def add_pacman_stuff(maze, max_food):
    """Add PacMen and food. """

    h, w = maze.shape

    ## starting pacmen positions
    maze[-2, 1] = '2'
    maze[-3, 1] = '0'
    maze[1, -2] = '3'
    maze[2, -2] = '1'

    ## random food
    total_food = 0
    while total_food < max_food:
        row = random.randint(1, h-2)
        col = random.randint(1, w//2-2)
        if (row > h - 6) and (col < 6): continue
        if maze[row, col] == E:
            maze[row, col] = F
            maze[h - row - 1, w - col - 1] = F
            total_food += 2


def get_new_maze(height, width, nfood=30, seed=None, dead_ends=False):
    """Create a new maze in text format.

    The maze is created with a recursive creation algorithm. The maze part of
    the blue team is a center-mirror version of the one for the red team.

    The function reserves space for 2 PacMan for each team in upper-right
    and lower-left corners of the maze. Food is added at random.

    Input arguments:
    height, width -- the size of the maze, including the outer walls
    nfood -- number of food dots for each team
    seed -- if not None, the random seed used to generate the maze
    dead_ends -- if False, remove all dead ends in the maze
    """

    if seed is None:
        seed = random.randint(1, 2 ** 31 - 1)
    random.seed(seed)

    print(f'Seed: {seed}', file=sys.stderr)

    maze = empty_maze(height, width)
    create_half_maze(maze, height // 2)

    # make space for pacman (2 pacman each)
    maze[-2, 1] = E
    maze[-3, 1] = E

    # remove dead ends
    if not dead_ends:
        remove_all_dead_ends(maze)

    # complete right part of maze with mirror copy
    maze[:, width // 2:] = numpy.flipud(numpy.fliplr(maze[:, :width // 2]))


    # add food and pacman
    add_pacman_stuff(maze, max_food=2 * nfood)

    # remove chamber
    remove_all_chambers(maze)

    return maze_to_bytes(maze)
