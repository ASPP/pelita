"""Detect if a layout contains "chambers" with food"""
import sys

import networkx
from pelita.layout import parse_layout


def get_hw(layout):
    walls = layout['walls']
    width = max([coord[0] for coord in walls]) + 1
    height = max([coord[1] for coord in walls]) + 1
    return height, width

def layout_to_graph(layout):
    """Return a networkx.Graph object given the layout
    """
    graph = networkx.Graph()
    height, width = get_hw(layout)
    walls = layout['walls']
    for x in range(width):
        for y in range(height):
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


def detect_chambers(graph, length):
    # loop through all the nodes
    chambers = []
    for node in graph:
        # only detect in the left half of the maze, we know the maze is symmetric
        if node[0] >= (length//2 -1):
            continue
        # make a local copy of the graph
        G = graph.copy()
        # remove the current node and check if we split the graph in two
        G.remove_node(node)
        # sort the subgraphs by length, shortest first
        subgraphs = sorted(networkx.connected_components(G), key=len)
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
    return chambers

flname = sys.argv[1]
with open(flname, "rt") as fl:
    layout = parse_layout(fl.read())

# first of all, check for simmetry
# if something is found on the left, it should be found center-mirrored on the right
height, width = get_hw(layout)
for x in range(width // 2):
    for y in range(height):
        coord = (x, y)
        cmirror = (width-x-1, height-y-1)
        for typ_ in ('walls', 'food'):
            if coord in layout[typ_]:
                assert cmirror in layout[typ_], "Layout is not symmetric!"


graph = layout_to_graph(layout)

connectivity = networkx.node_connectivity(graph)
# when connectivity is 1, there is at least one node that when removed
# splits the graph in two.
if connectivity < 2:
    chambers = detect_chambers(graph, width)
    # check if there is food in the chambers
    food_chambers = []
    for chamber in chambers:
        count = 0
        for node in chamber:
            if node in layout['food']:
                count += 1
        if count:
            food_chambers.append((chamber, count, chamber.pop()))

    if len(food_chambers) > 0:
        repr_nodes = [chamber[2] for chamber in food_chambers]
        print(f'{flname}: Detected {len(food_chambers)} food chamber(s): {repr_nodes}')
        # print the cut node and its companion on the other side of the maze
        #mirror = width-cut[0]-1, height-cut[1]-1
        #print(f'{flname}: {cut},{mirror} - food: {count}')
        #break
    else:
        repr_nodes = [chamber.pop() for chamber in chambers]
        print(f'{flname}: Detected {len(chambers)} empty chamber(s): {repr_nodes}')

