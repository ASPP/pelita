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


def add_wall_and_split(partition, walls, ngaps, vertical, rng=None):
    rng = default_rng(rng)

    (xmin, ymin), (xmax, ymax) = partition

    # the size of the maze partition we work on
    width = xmax - xmin + 1
    height = ymax - ymin + 1

    # if the partition is too small, stop
    if height < 3 and width < 3:
        return walls

    # insert a wall only if there is some space in the around it in the
    # orthogonal direction, i.e.:
    # if the wall is vertical, then the relevant length is the width
    # if the wall is horizontal, then the relevant length is the height
    partition_length = width if vertical else height
    if partition_length < rng.randint(3, 5):
        return walls

    # the raw/column to put the horizontal/vertical wall on
    # the position is calculated starting from the left/top of the maze partition
    # and then a random offset is added -> the resulting raw/column must not
    # exceed the available length
    pos = xmin if vertical else ymin
    pos += rng.randint(1, partition_length - 2)

    # the maximum length of the wall is the space we have in the same direction
    # of the wall in the partition, i.e.
    # if the wall is vertical, the maximum length is the height
    # if the wall is horizontal, the maximum length is the width
    max_length = height if vertical else width

    # We can start with a full wall, but we want to make sure that we do not
    # block the entrances to this partition. The entrances are
    # - the tile before the beginning of this wall [entrance] and
    # - the tile after the end of this wall [exit]
    # if entrance or exit are _not_ walls, then the wall must leave the neighboring
    # tiles also empty, i.e. the wall must be shortened accordingly
    if vertical:
        entrance_before = (pos, ymin - 1)
        entrance_after = (pos, ymin + max_length)
        begin = 0 if entrance_before in walls else 1
        end = max_length if entrance_after in walls else max_length-1
        wall = {(pos, ymin+y) for y in range(begin, end)}
    else:
        entrance_before = (xmin - 1, pos)
        entrance_after = (xmin + max_length, pos)
        begin = 0 if entrance_before in walls else 1
        end = max_length if entrance_after in walls else max_length-1
        wall = {(xmin+x, pos) for x in range(begin, end)}

    # place the requested number of gaps in the otherwise full wall
    # these gaps are indices in the direction of the wall, i.e.
    # x if horizontal and y if vertical
    # TODO: when we drop compatibility with numpy, this can be more easily done
    # by just sampling ngaps out of the full wall set, i.e.
    # gaps = rng.sample(wall, k=ngaps)
    # for gap in gaps:
    #     wall.remove(gap)
    ngaps = max(1, ngaps)
    wall_pos = list(range(max_length))
    rng.shuffle(wall_pos)

    for gap in wall_pos[:ngaps]:
        if vertical:
            wall.discard((pos, ymin+gap))
        else:
            wall.discard((xmin+gap, pos))

    # collect this wall into the global wall set
    walls |= wall

    # define the two new partitions of the maze generated by this wall
    # these are the parts of the maze to the left/right of a vertical wall
    # or the top/bottom of a horizontal wall
    if vertical:
        partitions = [((xmin,  ymin), (pos-1, ymax)),
                      ((pos+1, ymin), (xmax,  ymax))]
    else:
        partitions = [((xmin,  ymin), (xmax, pos-1)),
                      ((xmin, pos+1), (xmax,  ymax))]

    for partition in partitions:
        walls |= add_wall_and_split(
            partition, walls, max(1, ngaps // 2), not vertical, rng=rng
        )

    return walls


def generate_half_maze(width, height, ngaps_center, bots_pos, rng=None):
    # use binary space partitioning
    rng = default_rng(rng)

    # outer walls are top, bottom, left and right edge
    walls = {(x, 0) for x in range(width)} | \
            {(x, height-1) for x in range(width)} | \
            {(0, y) for y in range(height)} | \
            {(width-1, y) for y in range(height)}

    # Generate a wall with gaps at the border between the two homezones
    # in the left side of the maze

    # TODO: when we decide to break backward compatibility with the numpy version
    # of create maze, this part can be delegated directly to generate_walls and
    # then we need to rewrite mirror to mirror a set of coordinates around the center
    # by discarding the lower part of the border

    # Let us start with a full wall at the left side of the border
    x_wall = width//2 - 1
    wall = {(x_wall, y) for y in range(1, height - 1)}

    # possible locations for gaps
    # these gaps need to be symmetric around the center
    # TODO: when we decide to break compatibility with the numpy version of
    # create_maze we can rewrite this. See generate_walls for an example
    ymax = (height - 2) // 2
    candidates = list(range(ymax))
    rng.shuffle(candidates)

    for gap in candidates[:ngaps_center//2]:
        wall.remove((x_wall, gap+1))
        wall.remove((x_wall, ymax*2 - gap))

    walls |= wall
    partition = ((1, 1), (x_wall - 1, ymax * 2))

    walls = add_wall_and_split(
        partition,
        walls,
        ngaps_center // 2,
        vertical=False,
        rng=rng,
    )

    # make space for the pacmen:
    for bot in bots_pos:
        if bot in walls:
            walls.remove(bot)

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
