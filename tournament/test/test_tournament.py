#!/usr/bin/env python3

import unittest

from tournament import komode
from tournament import tournament

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


class TestTournament(unittest.TestCase):
    def test_match_winner(self):
        c = {
            "location": None,
            "date": None,
            "bonusmatch": None,
            "teams": [
                {"id": "group0", "spec": "StoppingPlayer", "members": []},
                {"id": "group1", "spec": "FoodEatingPlayer", "members": []},
            ]

        }
        config = tournament.Config(c)

        # group1 should win
        self.assertEqual(1, tournament.start_match(config, ["group0", "group1"]))
        self.assertEqual(0, tournament.start_match(config, ["group1", "group0"]))
        self.assertEqual(False, tournament.start_match(config, ["group0", "group0"]))


    def test_game_winner(self):
        c = {
            "location": None,
            "date": None,
            "bonusmatch": None,
            "teams": [
                {"id": "group0", "spec": "StoppingPlayer", "members": []},
                {"id": "group1", "spec": "FoodEatingPlayer", "members": []},
                {"id": "group2", "spec": "StoppingPlayer", "members": []},
                {"id": "group3", "spec": "StoppingPlayer", "members": []},
                {"id": "group4", "spec": "StoppingPlayer", "members": []},
            ]

        }
        print(12345)
        config = tournament.Config(c)
        print(12345)

        # group1 should win
        self.assertEqual(1, tournament.start_match(config, ["group0", "group1"]))
        self.assertEqual(0, tournament.start_match(config, ["group1", "group0"]))
        self.assertEqual(False, tournament.start_match(config, ["group0", "group0"]))
