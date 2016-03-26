#!/usr/bin/env python3

import unittest

import komode

class TestKoMode(unittest.TestCase):
    def test_sort_ranks(self):
        sort_ranks = komode.sort_ranks
        self.assertListEqual(sort_ranks(range(7)), [0, 5, 1, 4, 2, 3, 6])
        self.assertListEqual(sort_ranks(range(4)), [0, 3, 1, 2])
        self.assertListEqual(sort_ranks(range(2)), [0, 1])
        self.assertListEqual(sort_ranks(range(1)), [0])
        self.assertListEqual(sort_ranks([]), [])

    def test_prepared_matches(self):
        print(komode.prepare_matches([1]))
        print()
        print(komode.prepare_matches([1,2]))
        print()
        print(komode.prepare_matches([1,2,3]))
        print()
        print(komode.prepare_matches([1,2,3,4,5,6]))
        print()
        print(komode.prepare_matches([1,2,3,4,5]))
