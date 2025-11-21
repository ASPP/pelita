"""
Generate mazes for pelita

The algorithm is a form of binary space partitioning:

* start with an empty grid enclosed by walls
* draw a wall with k gaps, dividing the grid in 2 partitions
* repeat recursively for each sub-partitions, where walls have k/2 gaps
* pacmen are always in the bottom left and in the top right
* Food is distributed according to specifications

Notes:
The final maze includes is created by first generating the left half maze and then
generating the right half by making mirroring the left half. The resulting maze is
centrosymmetric.

Definitions:
Articulation point - a node in the graph that if removed would disconnect the
    graph in to two subgraphs. Find them with: nx.articulation_points(graph)

Dead-end - nodes in the graph with connectivity 1 -> that node is necessarily
    connected to an articulation point. Find them with
    {node for node in graph if graph.degree(node) == 1}

Tunnel: nodes in a sequence of articulation points connecting with a dead-end

Chamber: nodes connected to the main graph by a single articulation point -> it
    is basically a space with an entrance of a single node


Inspired by code by Dan Gillick
Completely rewritten by Pietro Berkes
Rewritten again (but not completely) by Tiziano Zito
Rewritten completely by Jakob Zahn & Tiziano Zito
"""

import networkx as nx

from .base_utils import default_rng
from .team import walls_to_graph

MIN_WIDTH = 5
MIN_HEIGHT = 5
PADDING = 2

def mirror(nodes, width, height):
    nodes = set(nodes)
    other = set((width - 1 - x, height - 1 - y) for x, y in nodes)
    return nodes | other


def sample_nodes(nodes, k, rng=None):
    rng = default_rng(rng)

    if k < len(nodes):
        return set(rng.sample(sorted(nodes), k=k))
    else:
        return nodes


def find_trapped_tiles(graph, width, include_chambers=False):
    main_chamber = set()
    chamber_tiles = set()

    for chamber in nx.biconnected_components(graph):
        max_x = max(chamber, key=lambda n: n[0])[0]
        min_x = min(chamber, key=lambda n: n[0])[0]
        if min_x < width // 2 <= max_x:
            # only the main chamber covers both sides
            # our own mazes should only have one central chamber
            # but other configurations could have more than one
            main_chamber.update(chamber)
            continue
        else:
            chamber_tiles.update(set(chamber))

    # remove shared articulation points with the main chamber
    chamber_tiles -= main_chamber

    # combine connected subgraphs
    if include_chambers:
        subgraphs = graph.subgraph(chamber_tiles)
        chambers = list(nx.connected_components(subgraphs))
    else:
        chambers = []

    return chamber_tiles, chambers


def distribute_food(all_tiles, chamber_tiles, trapped_food, total_food, rng=None):
    rng = default_rng(rng)

    if trapped_food > total_food:
        raise ValueError(
            f"number of trapped food ({trapped_food}) must not exceed total number of food ({total_food})"
        )

    if total_food > len(all_tiles):
        raise ValueError(
            f"number of total food ({total_food}) exceeds available tiles in maze ({len(all_tiles)})"
        )

    free_tiles = all_tiles - chamber_tiles

    # distribute as much trapped food in chambers as possible
    tf_pos = sample_nodes(chamber_tiles, trapped_food, rng=rng)

    # distribute remaining food outside of chambers
    free_food = total_food - len(tf_pos)

    ff_pos = sample_nodes(free_tiles, free_food, rng=rng)

    # there were not enough tiles to distribute all leftover food
    leftover_food = total_food - len(ff_pos) - len(tf_pos)
    if leftover_food > 0:
        leftover_tiles = chamber_tiles - tf_pos
        leftover_food_pos = sample_nodes(leftover_tiles, leftover_food, rng=rng)
    else:
        leftover_food_pos = set()

    return tf_pos | ff_pos | leftover_food_pos


def sample(x, k, rng):
    # temporary replacement wrapper for `rng.shuffle` conformant with
    # the `random.sample` API (minus the `count` parameter)

    # copy population
    result = x.copy()

    # shuffle all items
    rng.shuffle(result)

    # return the first `k` results
    return result[:k]


def order_preserved(a, b):
    # preserve the order of arguments
    return a, b


def order_inverted(a, b):
    # invert the order of arguments
    return b, a


def add_wall_and_split(partition, walls, ngaps, vertical, rng=None):
    rng = default_rng(rng)

    # ensure a connected maze by a minimum of 1 sampled gap
    ngaps = max(1, ngaps)

    # copy framing walls to avoid side effects
    walls = walls.copy()

    # store partitions in an expanding list alongside the number of gaps and
    # the orientation of the wall
    partitions = [partition + (ngaps, vertical)]

    # loop over all occuring partitions in the list;
    # the loop always exits because partitions always shrink by definition,
    # no new partitions are added once they shrank below a threshold and
    # the list of partitions is always drained on every iteration
    while len(partitions) > 0:
        #
        # DEFINITIONS
        #
        # a partition with its variables in `u`-`v`-space is described as:
        #
        # ┌─► u
        # ▼
        # v         umin       pos        umax
        #
        #            |          |          |
        #   vmin  ── O──────────O──────────┐
        #            │ pmin     │ wmin     │
        #            │          │          │
        #            │          │          │
        #            │          │          │
        #            │          │          │
        #   vmax  ── └──────────O──────────O
        #                         wmax       pmax

        # get the next partition
        pmin, pmax, ngaps, vertical = partitions.pop()
        xmin, ymin = pmin
        xmax, ymax = pmax

        # if vertical, preserve the coordinates, else transpose them
        order = order_preserved if vertical else order_inverted

        # map `x`-`y`-coordinates into `u`-`v`-space where the inner wall is
        # always vertical
        (umin, umax), (vmin, vmax) = order((xmin, xmax), (ymin, ymax))

        # the size of the maze partition we work on in `u`-`v`-space
        ulen = umax - umin + 1
        vlen = vmax - vmin + 1

        # if the partition is too small, move on with the next one
        if ulen < MIN_WIDTH and vlen < MIN_HEIGHT:
            continue

        # insert a wall only if there is some space around it in the
        # orthogonal `u`-direction, otherwise move on with the next partition
        if ulen < rng.randint(MIN_WIDTH, MIN_WIDTH + 2):
            continue

        #
        # WALL SAMPLING
        #

        # choose a coordinate within the partition length in `u`-direction
        pos = rng.randint(umin + PADDING, umax - PADDING)

        # define start and end of the inner wall in `x`-`y`-space
        wmin = order(pos, vmin)
        wmax = order(pos, vmax)

        # set start and end for the wall slice dependent on present entrances
        above = 1 if wmin in walls else 2
        below = 1 if wmax in walls else 2

        # sliced continuous wall in `x`-`y`-space
        wall = {order(pos, v) for v in range(vmin + above, vmax - below + 1)}

        # sample gap coordinates along the wall, i.e in `v`-direction
        #
        # TODO: 
        # when we drop compatibility with numpy mazes, the range of sampled
        # gaps can be adjusted to remove them directly from the full wall
        # OR we sample the wall segments to keep with k = len(wall) - ngaps
        gaps = list(range(vmin + 1, vmax))
        gaps = sample(gaps, ngaps, rng)

        # combine gap coordinates to wall gaps in `x`-`y`-space
        sampled = {order(pos, v) for v in gaps}

        # remove sampled gaps from the wall
        wall -= sampled

        # collect this wall into the global wall set
        walls |= wall

        #
        # SPLITTING
        #

        # we split the partition in 2, so we divide the number of gaps by 2;
        # ensure a connected maze with a minimum of 1 sampled gap
        ngaps = max(1, ngaps // 2)

        # define new partitions inscribed in the current one, split by the wall;
        # this definition is true for vertical and horizontal walls
        new = (
            # top/left
            (pmin, wmax, ngaps, not vertical),
            # bottom/right
            (wmin, pmax, ngaps, not vertical),
        )

        # queue the new partitions next
        #
        # TODO:
        # when we drop compatibility with numpy mazes, remove inversion
        partitions.extend(new[::-1])

    return walls


def generate_half_maze(width, height, ngaps_center, bots_pos, rng=None):
    # use binary space partitioning
    rng = default_rng(rng)

    # outer walls are top, bottom, left and right edge
    walls = {(x, 0) for x in range(width)} | \
            {(x, height-1) for x in range(width)} | \
            {(0, y) for y in range(height)} | \
            {(width-1, y) for y in range(height)}

    #
    # BORDER SAMPLING
    #
    # generate a wall with gaps at the border between the two homezones
    # in the left side of the maze

    # start with a full wall at the left side of the border
    x_wall = width//2 - 1
    wall = {(x_wall, y) for y in range(1, height - 1)}

    # possible locations for gaps
    # these gaps need to be symmetric around the center
    #
    # TODO:
    # when we drop compatibility with numpy mazes, this might be rewritten to
    # sample wall segments to keep with k = len(wall) - ngaps
    ymax = (height - 2) // 2
    candidates = list(range(ymax))
    candidates = sample(candidates, ngaps_center//2, rng)

    # remove gaps from top and mirrored from bottom
    for gap in candidates:
        wall.remove((x_wall, gap + 1))
        wall.remove((x_wall, height - 2 - gap))

    # collect the border into the global wall set
    walls |= wall

    #
    # BINARY SPACE PARTITIONING
    #

    # define the left homezone as the first partition to split
    partition = ((0, 0), (x_wall, height - 1))

    # run the binary space partitioning
    walls = add_wall_and_split(
        partition,
        walls,
        ngaps_center // 2,
        vertical=False,
        rng=rng,
    )

    # make space for the pacmen
    walls -= bots_pos

    return walls


def generate_maze(trapped_food=10, total_food=30, width=32, height=16, rng=None):
    if width % 2 != 0:
        raise ValueError(f"Width must be even ({width} given)")

    if width < 4:
        raise ValueError(f"Width must be at least 4, but {width} was given")

    if height < 4:
        raise ValueError(f"Height must be at least 4, but {height} was given")

    rng = default_rng(rng)

    # generate a full maze, but only the left half is filled with random walls
    # this allows us to cut the execution time in two, because the following
    # graph operations are quite expensive
    pacmen_pos = set([(1, height - 3), (1, height - 2)])
    walls = generate_half_maze(width, height, height//2, pacmen_pos, rng=rng)

    ### TODO: hide the chamber_finding in another function, create the graph with
    # a wall on the right border + 1, so that find chambers works reliably and
    # we can get rid of the  {.... if tile[0] < border} in the following
    # also, improve find_trapped_tiles so that it does not use x and width, but just
    # requires two sets of nodes representing the left and the right of the border
    # and then the main chambers is that one that has a non-empty intersection
    # with both.

    # transform to graph to find dead ends and chambers for food distribution
    # IMPORTANT: we have to include one column of the right border in the graph
    # generation, or our algorithm to find chambers would get confused
    # Note: this only works because in the right side of the maze we have no walls
    # except for the surrounding ones.
    graph = walls_to_graph(walls, shape=(width//2+1, height))

    # the algorithm should actually guarantee this, but just to make sure, let's
    # fail if the graph is not fully connected
    if not nx.is_connected(graph):
        raise ValueError("Generated maze is not fully connected, try a different random seed")

    # this gives us a set of tiles that are "trapped" within chambers, i.e. tunnels
    # with a dead-end or a section of tiles fully enclosed by walls except for a single
    # tile entrance
    chamber_tiles, _ = find_trapped_tiles(graph, width, include_chambers=False)

    # we want to distribute the food only on the left half of the maze
    # make sure that the tiles available for food distribution do not include
    # those right on the border of the homezone
    # also, no food on the initial positions of the pacmen
    # IMPORTANT: the relevant chamber tiles are only those in the left side of
    # the maze. By detecting chambers on only half of the maze, we may still have
    # spurious chambers on the right side
    border = width//2 - 1
    chamber_tiles = {tile for tile in chamber_tiles if tile[0] < border} - pacmen_pos
    all_tiles = {(x, y) for x in range(border) for y in range(height)}
    free_tiles = all_tiles - walls - pacmen_pos
    left_food = distribute_food(free_tiles, chamber_tiles, trapped_food, total_food, rng=rng)

    # get the full maze with all walls and food by mirroring the left half
    food = mirror(left_food, width, height)
    walls = mirror(walls, width, height)
    layout = { "walls" : tuple(sorted(walls)),
               "food"  : sorted(food),
               "bots"  : [ (1, height - 3), (width - 2, 2),
                           (1, height - 2), (width - 2, 1) ],
               "shape" : (width, height) }

    return layout
