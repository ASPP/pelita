#!/usr/bin/env python3

import unittest
from unittest.mock import MagicMock

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


### ASSERTIONS:
# There must be exactly one game_state with finished=True

class TestSingleMatch(unittest.TestCase):
    def test_run_match(self):
        config = MagicMock()
        config.rounds = 200
        config.team_spec = lambda x: x
        config.viewer = 'ascii'
        config.filter = 'small'

        teams = ["StoppingPlayer", "StoppingPlayer"]
        (state, stdout, stderr) = tournament.run_match(config, teams)
        self.assertEqual(state['team_wins'], None)
        self.assertEqual(state['game_draw'], True)

        config.rounds = 200
        config.team_spec = lambda x: x
        config.viewer = 'ascii'
        teams = ["FoodEatingPlayer", "StoppingPlayer"]
        (state, stdout, stderr) = tournament.run_match(config, teams)
        print(state)
        self.assertEqual(state['team_wins'], 0)
        self.assertEqual(state['game_draw'], None)

        config.rounds = 200
        config.team_spec = lambda x: x
        config.viewer = 'ascii'
        teams = ["StoppingPlayer", "FoodEatingPlayer"]
        (state, stdout, stderr) = tournament.run_match(config, teams)
        self.assertEqual(state['team_wins'], 1)
        self.assertEqual(state['game_draw'], None)

    def test_start_match(self):
        stdout = []

        def mock_print(str="", *args, **kwargs):
            print(str)
            stdout.append(str)

        teams = {
            "first_id": "StoppingPlayer",
            "second_id": "FoodEatingPlayer",
        }

        config = MagicMock()
        config.rounds = 300
        config.team_spec = lambda x: teams[x]
        config.team_name = lambda x: teams[x]
        config.viewer = 'ascii'
        config.filter = 'small'
        config.print = mock_print

        team_ids = ["first_id", "first_id"]
        result = tournament.start_match(config, team_ids)
        self.assertEqual(result, False)
        self.assertEqual(stdout[-1], '‘StoppingPlayer’ and ‘StoppingPlayer’ had a draw.')

        team_ids = ["second_id", "first_id"]
        result = tournament.start_match(config, team_ids)
        self.assertEqual(result, "second_id")
        self.assertEqual(stdout[-1], '‘FoodEatingPlayer’ wins')

        team_ids = ["first_id", "second_id"]
        result = tournament.start_match(config, team_ids)
        self.assertEqual(result, "second_id")
        self.assertEqual(stdout[-1], '‘FoodEatingPlayer’ wins')


    def test_deathmatch(self):
        stdout = []

        def mock_print(str="", *args, **kwargs):
            stdout.append(str)

        teams = {
            "first_id": "StoppingPlayer",
            "second_id": "StoppingPlayer",
        }

        config = MagicMock()
        config.rounds = 200
        config.teams = teams
        config.team_spec = lambda x: teams[x]
        config.team_name = lambda x: teams[x]
        config.viewer = 'ascii'
        config.filter = 'small'
        config.print = mock_print

        result = tournament.start_deathmatch(config, *teams.keys())
        self.assertIsNotNone(result)
        self.assertIn(result, ["first_id", "second_id"])



class TestTournament(unittest.TestCase):
    def test_tournament_winner(self):
        stdout = []

        def mock_print(str="", *args, **kwargs):
            stdout.append(str)

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
            ],
            "filter": "small",
        }
        config = tournament.Config(c)
        config.print = mock_print
        config.viewer = 'null'
        config.state = None

        # group1 should win
        self.assertEqual("group1", tournament.start_match(config, ["group0", "group1"]))
        self.assertEqual("group1", tournament.start_match(config, ["group1", "group0"]))
        self.assertEqual(False, tournament.start_match(config, ["group0", "group0"]))

        tournament.present_teams(config)

        state = tournament.State(config)
        rr_ranking = tournament.round1(config, state)

        if config.bonusmatch:
            sorted_ranking = komode.sort_ranks(rr_ranking[:-1]) + [rr_ranking[-1]]
        else:
            sorted_ranking = komode.sort_ranks(rr_ranking)

        winner = tournament.round2(config, sorted_ranking, state)
        self.assertEqual(winner, 'group1')