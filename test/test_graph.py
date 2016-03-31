import unittest

from pelita.datamodel import CTFUniverse, east, north, south, stop, west
from pelita.graph import (AdjacencyList, NoPathException, diff_pos, iter_adjacencies,
                          manhattan_dist, new_pos)


class TestStaticmethods(unittest.TestCase):

    def test_new_pos(self):
        self.assertEqual(new_pos((1, 1), north), (1, 0))
        self.assertEqual(new_pos((1, 1), south), (1, 2))
        self.assertEqual(new_pos((1, 1), east), (2, 1))
        self.assertEqual(new_pos((1, 1), west), (0, 1))
        self.assertEqual(new_pos((1, 1), stop), (1, 1))
        self.assertEqual(new_pos((0, 0), (1, 1)), (1, 1))

    def test_diff_pos(self):
        self.assertEqual(north, diff_pos((1, 1), (1, 0)))
        self.assertEqual(south, diff_pos((1, 1), (1, 2)))
        self.assertEqual(east, diff_pos((1, 1), (2, 1)))
        self.assertEqual(west, diff_pos((1, 1), (0, 1)))
        self.assertEqual(stop, diff_pos((1, 1), (1, 1)))

    def test_diff_pos_arbitrary(self):
        vectors = [(0, 0), (0, 1), (-1, 1), (-2, 3)]
        orig = (1, 1)
        for vec in vectors:
            new = new_pos(orig, vec)
            self.assertEqual(vec, diff_pos(orig, new))

    def test_manhattan_dist(self):
        self.assertEqual(0, manhattan_dist((0, 0), (0, 0)))
        self.assertEqual(0, manhattan_dist((1, 1), (1, 1)))
        self.assertEqual(0, manhattan_dist((20, 20), (20, 20)))

        self.assertEqual(1, manhattan_dist((0, 0), (1, 0)))
        self.assertEqual(1, manhattan_dist((0, 0), (0, 1)))
        self.assertEqual(1, manhattan_dist((1, 0), (0, 0)))
        self.assertEqual(1, manhattan_dist((0, 1), (0, 0)))

        self.assertEqual(2, manhattan_dist((0, 0), (1, 1)))
        self.assertEqual(2, manhattan_dist((1, 1), (0, 0)))
        self.assertEqual(2, manhattan_dist((1, 0), (0, 1)))
        self.assertEqual(2, manhattan_dist((0, 1), (1, 0)))
        self.assertEqual(2, manhattan_dist((0, 0), (2, 0)))
        self.assertEqual(2, manhattan_dist((0, 0), (0, 2)))
        self.assertEqual(2, manhattan_dist((2, 0), (0, 0)))
        self.assertEqual(2, manhattan_dist((0, 2), (0, 0)))

        self.assertEqual(4, manhattan_dist((1, 2), (3, 4)))

    def test_iter_adjacencies(self):
        def onedim_lattice(n, max_size):
            return [neighbour for neighbour in [n - 1, n + 1] if abs(neighbour) <= max_size]

        # starting at 0, we’ll get all 21 points:
        adjs0 = list(iter_adjacencies([0], lambda n: onedim_lattice(n, 10)))
        self.assertEqual(21, len(adjs0))
        self.assertEqual(set(range(-10, 11)), set(dict(adjs0).keys()))

        # starting at 11, we’ll get 22 points
        adjs1 = list(iter_adjacencies([11], lambda n: onedim_lattice(n, 10)))
        self.assertEqual(22, len(adjs1))
        self.assertEqual(set(range(-10, 12)), set(dict(adjs1).keys()))

        # starting at 12, we’ll get 1 point
        adjs2 = list(iter_adjacencies([12], lambda n: onedim_lattice(n, 10)))
        self.assertEqual(1, len(adjs2))
        self.assertEqual([(12, [])], list(adjs2))

        # starting at [0, 12], we’ll get adjs0 | adjs2
        adjs3 = list(iter_adjacencies([0, 12], lambda n: onedim_lattice(n, 10)))
        self.assertEqual(22, len(adjs3))
        self.assertEqual(sorted(adjs0 + adjs2), sorted(adjs3))

class TestAdjacencyList(unittest.TestCase):

    def test_pos_within(self):
        test_layout = (
        """ ##################
            #0#.  .  # .     #
            #2#####    #####1#
            #     . #  .  .#3#
            ################## """)
        universe = CTFUniverse.create(test_layout, 4)
        al = AdjacencyList(universe.free_positions())
        free = {pos for pos, val in universe.maze.items() if not val}

        self.assertFalse((0, 0) in al)
        self.assertRaises(NoPathException, al.pos_within, (0, 0), 0)
        self.assertFalse((6, 2) in al)
        self.assertRaises(NoPathException, al.pos_within, (6, 2), 0)

        self.assertTrue((1, 1) in al)
        self.assertEqual(set([(1, 1)]), al.pos_within((1, 1), 0))
        target = set([(1, 1), (1, 2), (1,3), (2, 3), (3, 3), (3, 3)])
        self.assertEqual(target, al.pos_within((1, 1), 5))
        # assuming a_star is working properly
        for pos in target:
            self.assertTrue(len(al.a_star((1, 1), pos)) < 5)
        for pos in free.difference(target):
            self.assertTrue(len(al.a_star((1, 1), pos)) >= 5)

    def test_basic_adjacency_list(self):
        test_layout = (
        """ ######
            #    #
            ###### """)
        universe = CTFUniverse.create(test_layout, 0)
        al = AdjacencyList(universe.free_positions())
        target = { (4, 1): [(4, 1), (3, 1)],
                   (1, 1): [(2, 1), (1, 1)],
                   (2, 1): [(3, 1), (2, 1), (1, 1)],
                   (3, 1): [(4, 1), (3, 1), (2, 1)]}

        for val in al.values():
            val.sort()

        for val in target.values():
            val.sort()

        self.assertEqual(target, al)

    def test_extended_adjacency_list(self):
        test_layout = (
        """ ##################
            #0#.  .  # .     #
            # #####    ##### #
            #     . #  .  .#1#
            ################## """)
        universe = CTFUniverse.create(test_layout, 2)
        al = AdjacencyList(universe.free_positions())

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

        for val in al.values():
            val.sort()

        for val in adjacency_target.values():
            val.sort()

        self.assertEqual(adjacency_target, al)

    def test_bfs_to_self(self):
        test_layout = (
        """ ############
            #0.     #.1#
            ############ """)
        universe = CTFUniverse.create(test_layout, 2)
        al = AdjacencyList(universe.free_positions())
        self.assertEqual([], al.bfs((1,1), [(1, 1), (2, 1)]))

    def test_a_star(self):
        test_layout = (
        """ ##################
            #0#.  .  # .     #
            #2#####    #####1#
            #     . #  .  .#3#
            ################## """)
        universe = CTFUniverse.create(test_layout, 4)
        al = AdjacencyList(universe.free_positions())
        # just a simple smoke test
        self.assertEqual(14, len(al.a_star((1, 1), (3, 1))))

    def test_path_to_same_position(self):
        test_layout = (
        """ ##################
            #0#.  .  # .     #
            #2#####    #####1#
            #     . #  .  .#3#
            ################## """)
        universe = CTFUniverse.create(test_layout, 4)
        al = AdjacencyList(universe.free_positions())
        self.assertEqual([], al.a_star((1, 1), (1, 1)))
        self.assertEqual([], al.bfs((1, 1), [(1, 1)]))

    def test_bfs_exceptions(self):
        test_layout = (
        """ ############
            #0.     #.1#
            ############ """)
        universe = CTFUniverse.create(test_layout, 2)
        al = AdjacencyList(universe.free_positions())
        self.assertRaises(NoPathException, al.bfs, (1, 1), [(10, 1)])
        self.assertRaises(NoPathException, al.bfs, (1, 1), [(10, 1), (9, 1)])
        self.assertRaises(NoPathException, al.bfs, (0, 1), [(10, 1)])
        self.assertRaises(NoPathException, al.bfs, (1, 1), [(11, 1)])

    def test_a_star_exceptions(self):
        test_layout = (
        """ ############
            #0.     #.1#
            ############ """)
        universe = CTFUniverse.create(test_layout, 2)
        al = AdjacencyList(universe.free_positions())
        self.assertRaises(NoPathException, al.a_star, (1, 1), (10, 1))
        self.assertRaises(NoPathException, al.a_star, (0, 1), (10, 1))
        self.assertRaises(NoPathException, al.a_star, (1, 1), (11, 1))
