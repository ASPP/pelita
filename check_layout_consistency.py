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

if __name__ == '__main__':

    # either read a file or read from stdin
    if len(sys.argv) == 1:
        flname = 'stdin'
        layout = parse_layout(sys.stdin.read())
    else:
        flname = sys.argv[1]
        with open(flname, "rt") as fl:
            layout = parse_layout(fl.read())

    # first of all, check for simmetry
    # if something is found on the left, it should be found center-mirrored on the right
    height, width = get_hw(layout)
    known = layout['walls']+layout['food']
    layout['empty'] = [(x,y) for x in range(width) for y in range(height) if (x,y) not in known]
    for x in range(width // 2):
        for y in range(height):
            coord = (x, y)
            cmirror = (width-x-1, height-y-1)
            for typ_ in ('walls', 'food', 'empty'):
                if (coord in layout[typ_]) and (cmirror not in layout[typ_]):
                        print(f'{flname}: Layout is not symmetric {coord} != {cmirror}')


    graph = layout_to_graph(layout)

    # check for dead_ends
    for node, degree in graph.degree():
        if degree < 2:
            print(f'{flname}: found dead end in {node}')

    if networkx.node_connectivity(graph) < 2:
        entrance = networkx.minimum_node_cut(graph).pop()
        print(f'{flname}: Detected chamber, entrance: {entrance}')

