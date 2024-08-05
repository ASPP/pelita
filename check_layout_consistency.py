"""Detect if a layout contains "chambers" with food"""
import sys

import networkx as nx
from pelita.layout import parse_layout
from pelita.utils import walls_to_graph


if __name__ == '__main__':

    # either read a file or read from stdin
    if len(sys.argv) == 1:
        flname = 'stdin'
        layout = parse_layout(sys.stdin.read())
    else:
        flname = sys.argv[1]
        with open(flname, "rt") as fl:
            layout = parse_layout(fl.read())

    # first of all, check for symmetry
    # if something is found on the left, it should be found center-mirrored on the right
    width, height = layout['shape']
    known = set(layout['walls']) | set(layout['food'])
    layout['empty'] = [(x,y) for x in range(width) for y in range(height) if (x,y) not in known]
    for x in range(width // 2):
        for y in range(height):
            coord = (x, y)
            cmirror = (width-x-1, height-y-1)
            for typ_ in ('walls', 'food', 'empty'):
                if (coord in layout[typ_]) and (cmirror not in layout[typ_]):
                        print(f'{flname}: Layout is not symmetric {coord} != {cmirror}')


    graph = walls_to_graph(layout['walls'])

    # check for dead_ends
    for node, degree in graph.degree():
        if degree < 2:
            print(f'{flname}: found dead end in {node}')

    if nx.node_connectivity(graph) < 2:
        entrance = nx.minimum_node_cut(graph).pop()
        print(f'{flname}: Detected chamber, entrance: {entrance}')

