# -*- coding: utf-8 -*-

""" Basic graph module """

from pelita.datamodel import Maze, Free

__docformat__ = "restructuredtext"

class NoPathException(Exception):
    pass

class AdjacencyList(dict):

    def __init__(self, universe):
        # Get the list of all free positions.
        free_pos = universe.maze.pos_of(Free)
        # Here we use a generator on a dictionary to create the adjacency list.
        self.adjacency = dict((pos, universe.get_legal_moves(pos).values())
                for pos in free_pos)
