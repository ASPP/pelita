#!/usr/bin/env python3

import unittest

import re
from textwrap import dedent

from tournament import komode, roundrobin, tournament
from tournament.komode import Team, Match, Bye
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
        with self.assertRaises(ValueError):
            none = komode.prepare_matches([])
        with self.assertRaises(ValueError):
            none = komode.prepare_matches([], bonusmatch=True)

        single = komode.prepare_matches([1])
        self.assertEqual(single, komode.Team(name=1))
        single = komode.prepare_matches([1], bonusmatch=True)
        self.assertEqual(single, komode.Team(name=1))

        pair = komode.prepare_matches([1,2])
        self.assertEqual(pair, Match(t1=Team(name=1), t2=Team(name=2)))
        pair = komode.prepare_matches([1,2], bonusmatch=True)
        self.assertEqual(pair, Match(t1=Team(name=1), t2=Team(name=2)))

        triple = komode.prepare_matches([1,2,3])
        self.assertEqual(triple, Match(t1=Match(t1=Team(name=1), t2=Team(name=2)), t2=Bye(team=Team(name=3))))
        triple = komode.prepare_matches([1,2,3], bonusmatch=True)
        self.assertEqual(triple, Match(t1=Match(t1=Team(name=1), t2=Team(name=2)), t2=Bye(team=Team(name=3))))

        matches = komode.prepare_matches([1,2,3,4])
        outcome = Match(t1=Match(t1=Team(name=1), t2=Team(name=2)), t2=Match(t1=Team(name=3), t2=Team(name=4)))
        self.assertEqual(matches, outcome)
        matches = komode.prepare_matches([1,2,3,4], bonusmatch=True)
        outcome = Match(t1=Match(t1=Match(t1=Team(name=1), t2=Team(name=2)), t2=Bye(team=Team(name=3))), t2=Bye(team=Bye(team=Team(name=4))))
        self.assertEqual(matches, outcome)

        matches = komode.prepare_matches([1,2,3,4,5])
        outcome = Match(t1=Match(t1=Match(t1=Team(name=1), t2=Team(name=2)), t2=Match(t1=Team(name=3), t2=Team(name=4))), t2=Bye(team=Bye(team=Team(name=5))))
        self.assertEqual(matches, outcome)
        matches = komode.prepare_matches([1,2,3,4,5], bonusmatch=True)
        outcome = Match(t1=Match(t1=Match(t1=Team(name=1), t2=Team(name=4)), t2=Match(t1=Team(name=2), t2=Team(name=3))), t2=Bye(team=Bye(team=Team(name=5))))
        self.assertEqual(matches, outcome)

        matches = komode.prepare_matches([1,2,3,4,5,6])
        outcome = Match(t1=Match(t1=Match(t1=Team(name=1), t2=Team(name=2)), t2=Match(t1=Team(name=3), t2=Team(name=4))), t2=Bye(team=Match(t1=Team(name=5), t2=Team(name=6))))
        self.assertEqual(matches, outcome)
        matches = komode.prepare_matches([1,2,3,4,5,6], bonusmatch=True)
        outcome = Match(t1=Match(t1=Match(t1=Match(t1=Team(name=1), t2=Team(name=4)), t2=Match(t1=Team(name=2), t2=Team(name=3))), t2=Bye(team=Bye(team=Team(name=5)))), t2=Bye(team=Bye(team=Bye(team=Team(name=6)))))
        self.assertEqual(matches, outcome)

    def test_output(self):
        matches = komode.prepare_matches([1,2,3,4,5,6])
        printed = komode.print_knockout(matches)
        # remove the whitespace to the right of the printed lines
        printed = re.sub(r'\s+$', '', printed, flags=re.MULTILINE)
        outcome = """\
         1 ┐
           ├─ ??? ┐
         2 ┘      │
                  ├─ ??? ┐
         3 ┐      │      │
           ├─ ??? ┘      │  ┏━━━━━┓
         4 ┘             ├──┨ ??? ┃
                         │  ┗━━━━━┛
         5 ┐             │
           ├─ ??? ───────┘
         6 ┘"""
        self.assertEqual(dedent(printed), dedent(outcome))

        matches = komode.prepare_matches([1,2,3,4,5,6], bonusmatch=True)
        printed = komode.print_knockout(matches)
        print(printed)
        # remove the whitespace to the right of the printed lines
        printed = re.sub(r'\s+$', '', printed, flags=re.MULTILINE)
        outcome = """\
         1 ┐
           ├─ ??? ┐
         4 ┘      │
                  ├─ ??? ┐
         2 ┐      │      │
           ├─ ??? ┘      ├─ ??? ┐
         3 ┘             │      │  ┏━━━━━┓
                         │      ├──┨ ??? ┃
         5 ──────────────┘      │  ┗━━━━━┛
                                │
         6 ─────────────────────┘"""
        self.assertEqual(dedent(printed), dedent(outcome))


class TestRoundRobin(unittest.TestCase):
    def test_shuffle(self):
        data = [
            ([], []),
            ([1], []),
            ([1, 2], [(1, 2)]),
            ([1, 2, 3], [(1, 2), (1, 3), (2, 3)]),
            ([1, 2, 3, 4], [(1, 2), (1, 3), (1, 4), (2, 3), (2, 4), (3, 4)])
        ]

        def tuple_sort(t):
            return tuple(sorted(list(t)))

        for input, output in data:
            d = roundrobin.initial_state(input)
            d = [tuple_sort(x) for x in d]
            output = [tuple_sort(x) for x in output]
            self.assertEqual(len(d), len(output))
            self.assertEqual(set(d), set(output))

        # TODO: Test that order is actually shuffled


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
