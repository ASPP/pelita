import json
from itertools import product

import jsbeautifier
import networkx as nx

from pelita.layout import get_available_layouts, get_layout_by_name, parse_layout
from pelita.maze_generator import find_chamber


def position_in_maze(pos, shape):
    x, y = pos
    w, h = shape

    return 0 <= x < w and 0 <= y < h


def walls_to_graph(walls, shape):
    w, h = shape
    directions = [(1, 0), (0, 1), (0, -1)]

    graph = nx.Graph()
    # define nodes for maze

    coords = product(range(w), range(h))
    not_walls = set(coords) - set(walls)

    edges = []
    for x, y in not_walls:
        # this is a free position, get its neighbors
        for delta_x, delta_y in directions:
            neighbor = (x + delta_x, y + delta_y)
            # we don't need to check for getting neighbors out of the maze
            # because our mazes are all surrounded by walls, i.e. our
            # deltas will not put us out of the maze
            if neighbor not in walls and position_in_maze(neighbor, shape):
                # this is a genuine neighbor, add an edge in the graph
                edges.append(((x, y), neighbor))

    graph.add_edges_from(edges)
    return graph


def find_cuts(graph):
    G = graph.copy()
    cuts = []
    while True:
        cut, chamber = find_chamber(G)
        if cut:
            G.remove_nodes_from(chamber)
            cuts.append(cut)
        else:
            break
    return cuts


def find_cuts_faster(graph):
    return list(nx.articulation_points(graph))


def find_chambers(graph, cuts, deadends, shape):
    w, h = shape
    G = graph.copy()

    nodes = cuts + deadends
    subgraph = graph.subgraph(nodes)
    tunnels = [sorted(t) for t in nx.connected_components(subgraph)]

    G.remove_nodes_from(nodes)

    # remove main chamber
    chambers = []
    for chamber in nx.connected_components(G):
        skip = False
        for node in chamber:
            if w // 2 - 1 <= node[0] <= w // 2:
                skip = True
                break

        if skip:
            continue

        chambers.extend(chamber)

    nodes = set(cuts + deadends + chambers)

    subgraph = graph.subgraph(nodes)
    chambers = [sorted(c) for c in nx.connected_components(subgraph)]

    # remove "fake" chambers only connected to articulation points
    # for c, chamber in enumerate(chambers):
    #    G = graph.copy()
    #    connections = []
    #    for edge in graph.edges:
    #        a, b = edge
    #        if (a in G.nodes and b in chamber) or (b in G.nodes and a in chamber):
    #            connections.append(edge)
    #    if connections:
    #        print("BICONNECTED")
    #        print(connections)
    #        print(chamber)

    return chambers


def paint_chambers(graph, cuts, shape):
    w, h = shape
    chamber_tiles = set()
    G = graph

    for cut in cuts:
        edges = list(G.edges(cut))
        G.remove_node(cut)

        # remove main chamber
        for chamber in nx.connected_components(G):
            max_x = max(chamber, key=lambda n: n[0])[0]
            min_x = min(chamber, key=lambda n: n[0])[0]
            if not (min_x < w // 2 and max_x >= w // 2):
                chamber_tiles.update(set(chamber))
        G.add_node(cut)
        G.add_edges_from(edges)

    subgraph = graph.subgraph(chamber_tiles)
    chambers = list(nx.connected_components(subgraph))

    return chambers, chamber_tiles


def chambers_to_food(
    layout: str,
    chambers: list[tuple[int, int]],
    temp_layout_path="/tmp/pelita_marked.layout",
):
    with open(temp_layout_path, mode="w") as temp_layout_file:
        line_number = 0
        for line in layout.splitlines():
            line = line.replace(".", " ")
            for x, y in chambers:
                if y == line_number and line[x] not in ["a", "b", "x", "y"]:
                    line = line[:x] + "." + line[x + 1 :]
            temp_layout_file.write(line + "\n")
            line_number += 1
        return temp_layout_path


def find_dead_ends(graph):
    """Find dead ends in a graph."""

    dead_ends = [node for node in graph.nodes() if graph.degree(node) == 1]
    return dead_ends


names = []

for size, deadend in [
    # ("small", False),
    # ("small", True),
    # ("normal", False),
    ("normal", True),
]:
    names.extend(get_available_layouts(size=size, dead_ends=deadend))

layouts = [get_layout_by_name(name) for name in names]
layouts = [parse_layout(layout) for layout in layouts]

objs = []

custom_layout = """################################
# ###     .          #.    .. y#
#    #### # ##### .  #.###   #x#
# #          .   . . #   #     #
#   ##    . .   ##.   ###.#### #
# # ####  #  .     ..#     . # #
#####  #  #  . ## .  #.#####.#.#
#     .#  ####.    . #  # .  # #
# #  . #  # .    .####  #.     #
#.#.#####.#  . ## .  #  #  . # #
# # .     #..     .  #  #### # #
# # ###.###   .##   . .     .  #
#     #   # . .   .     #  . # #
#a#   ###.#  . ##### # ### # # #
#b ..    .#          .       . #
################################
"""

# names = ["custom_layout"]
# layouts = [parse_layout(custom_layout)]

# names = ["normal_079"]
# layouts = [parse_layout(get_layout_by_name("normal_079"))]

for s, (name, layout) in enumerate(zip(names, layouts)):
    print(s)
    obj = dict()

    obj["name"] = name
    obj["shape"] = (width, height) = shape = layout["shape"]
    obj["food"] = len(layout["food"]) // 2

    walls = layout["walls"]

    graph = walls_to_graph(walls, shape)

    deadends = find_dead_ends(graph)
    obj["deadends"] = n_deadends = len(deadends) // 2

    cuts = find_cuts_faster(graph)
    chambers, chamber_tiles = paint_chambers(graph, cuts, shape)
    obj["chambers"] = n_chambers = len(chambers) // 2

    obj["chamber_size"] = len(chamber_tiles) // 2
    # chambers_to_food(get_layout_by_name(name), chamber_tiles, f"/tmp/{name}.layout")
    # chambers_to_food(custom_layout, chamber_tiles, f"/tmp/{name}.layout")

    if n_chambers == 0:
        assert n_deadends == 0

    objs.append(obj)

options = jsbeautifier.default_options()
options.indent_size = 2
with open("db.json", "wt") as db:
    db.write(jsbeautifier.beautify(json.dumps(objs), options))
