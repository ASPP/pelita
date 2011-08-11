# -*- coding: utf-8 -*-

import unittest
from pelita.datamodel import create_CTFUniverse, Free
from pelita.graph import AdjacencyList, NoPathException, NoPositionException

class TestAdjacencyList(unittest.TestCase):

    def test_basic_adjacency_list(self):
        test_layout = (
        """ ##################
            #0#.  .  # .     #
            # #####    ##### #
            #     . #  .  .#1#
            ################## """)
        universe = create_CTFUniverse(test_layout, 2)
        al = AdjacencyList(universe)

        adjacency_target = {(7, 3): [(7, 2), (7, 3), (6, 3)],
         (1, 3): [(1, 2), (2, 3), (1, 3)],
         (12, 1): [(13, 1), (12, 1), (11, 1)],
         (16, 2): [(16, 3), (16, 1), (16, 2)],
         (15, 1): [(16, 1), (15, 1), (14, 1)],
         (5, 1): [(6, 1), (5, 1), (4, 1)],
         (10, 3): [(10, 2), (11, 3), (10, 3), (9, 3)],
         (7, 2): [(7, 3), (7, 1), (8, 2), (7, 2)],
         (1, 2): [(1, 3), (1, 1), (1, 2)],
         (3, 3): [(4, 3), (3, 3), (2, 3)],
         (13, 3): [(14, 3), (13, 3), (12, 3)],
         (8, 1): [(8, 2), (8, 1), (7, 1)],
         (16, 3): [(16, 2), (16, 3)],
         (6, 3): [(7, 3), (6, 3), (5, 3)],
         (14, 1): [(15, 1), (14, 1), (13, 1)],
         (11, 1): [(12, 1), (11, 1), (10, 1)],
         (4, 1): [(5, 1), (4, 1), (3, 1)],
         (1, 1): [(1, 2), (1, 1)],
         (12, 3): [(13, 3), (12, 3), (11, 3)],
         (8, 2): [(8, 1), (9, 2), (8, 2), (7, 2)],
         (7, 1): [(7, 2), (8, 1), (7, 1), (6, 1)],
         (9, 3): [(9, 2), (10, 3), (9, 3)],
         (2, 3): [(3, 3), (2, 3), (1, 3)],
         (10, 1): [(10, 2), (11, 1), (10, 1)],
         (5, 3): [(6, 3), (5, 3), (4, 3)],
         (13, 1): [(14, 1), (13, 1), (12, 1)],
         (9, 2): [(9, 3), (10, 2), (9, 2), (8, 2)],
         (6, 1): [(7, 1), (6, 1), (5, 1)],
         (3, 1): [(4, 1), (3, 1)],
         (11, 3): [(12, 3), (11, 3), (10, 3)],
         (16, 1): [(16, 2), (16, 1), (15, 1)],
         (4, 3): [(5, 3), (4, 3), (3, 3)],
         (14, 3): [(14, 3), (13, 3)],
         (10, 2): [(10, 3), (10, 1), (10, 2), (9, 2)]}
        self.assertEqual(adjacency_target, al.adjacency)

    def test_bfs_exceptions(self):
        test_layout = (
        """ ############
            #0.     #.1#
            ############ """)
        universe = create_CTFUniverse(test_layout, 2)
        al = AdjacencyList(universe)
        self.assertRaises(NoPathException, al.bfs, (1, 1), [(10, 1)])
        self.assertRaises(NoPathException, al.bfs, (1, 1), [(10, 1), (9, 1)])
        self.assertRaises(NoPositionException, al.bfs, (0, 1), [(10, 1)])
        self.assertRaises(NoPositionException, al.bfs, (1, 1), [(11, 1)])

