import pytest
from unittest.mock import MagicMock

import sys
pytestmark = pytest.mark.skipif(sys.version_info < (3,5), reason="requires python3.5")

import re
from textwrap import dedent

try:
    from pelita.tournament import komode, roundrobin, tournament
    from pelita.tournament.komode import Team, Match, Bye
    from pelita.tournament import tournament
except (ImportError, SyntaxError):
    # We expect this to fail below Python 3.5
    pass


class TestKoMode:
    def test_sort_ranks(self):
        sort_ranks = komode.sort_ranks
        assert sort_ranks(range(7)) == [0, 5, 1, 4, 2, 3, 6]
        assert sort_ranks(range(4)) == [0, 3, 1, 2]
        assert sort_ranks(range(2)) == [0, 1]
        assert sort_ranks(range(1)) == [0]
        assert sort_ranks([]) == []

    def test_prepared_matches(self):
        with pytest.raises(ValueError):
            none = komode.prepare_matches([])
        with pytest.raises(ValueError):
            none = komode.prepare_matches([], bonusmatch=True)

        single = komode.prepare_matches([1])
        assert single == komode.Team(name=1)
        single = komode.prepare_matches([1], bonusmatch=True)
        assert single == komode.Team(name=1)

        pair = komode.prepare_matches([1,2])
        assert pair == Match(t1=Team(name=1), t2=Team(name=2))
        pair = komode.prepare_matches([1,2], bonusmatch=True)
        assert pair == Match(t1=Team(name=1), t2=Team(name=2))

        triple = komode.prepare_matches([1,2,3])
        assert triple == Match(t1=Match(t1=Team(name=1), t2=Team(name=2)), t2=Bye(team=Team(name=3)))
        triple = komode.prepare_matches([1,2,3], bonusmatch=True)
        assert triple == Match(t1=Match(t1=Team(name=1), t2=Team(name=2)), t2=Bye(team=Team(name=3)))

        matches = komode.prepare_matches([1,2,3,4])
        outcome = Match(t1=Match(t1=Team(name=1), t2=Team(name=2)), t2=Match(t1=Team(name=3), t2=Team(name=4)))
        assert matches == outcome
        matches = komode.prepare_matches([1,2,3,4], bonusmatch=True)
        outcome = Match(t1=Match(t1=Match(t1=Team(name=1), t2=Team(name=2)), t2=Bye(team=Team(name=3))), t2=Bye(team=Bye(team=Team(name=4))))
        assert matches == outcome

        matches = komode.prepare_matches([1,2,3,4,5])
        outcome = Match(t1=Match(t1=Match(t1=Team(name=1), t2=Team(name=2)), t2=Match(t1=Team(name=3), t2=Team(name=4))), t2=Bye(team=Bye(team=Team(name=5))))
        assert matches == outcome
        matches = komode.prepare_matches([1,2,3,4,5], bonusmatch=True)
        outcome = Match(t1=Match(t1=Match(t1=Team(name=1), t2=Team(name=4)), t2=Match(t1=Team(name=2), t2=Team(name=3))), t2=Bye(team=Bye(team=Team(name=5))))
        assert matches == outcome

        matches = komode.prepare_matches([1,2,3,4,5,6])
        outcome = Match(t1=Match(t1=Match(t1=Team(name=1), t2=Team(name=2)), t2=Match(t1=Team(name=3), t2=Team(name=4))), t2=Bye(team=Match(t1=Team(name=5), t2=Team(name=6))))
        assert matches == outcome
        matches = komode.prepare_matches([1,2,3,4,5,6], bonusmatch=True)
        outcome = Match(t1=Match(t1=Match(t1=Match(t1=Team(name=1), t2=Team(name=4)), t2=Match(t1=Team(name=2), t2=Team(name=3))), t2=Bye(team=Bye(team=Team(name=5)))), t2=Bye(team=Bye(team=Bye(team=Team(name=6)))))
        assert matches == outcome

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
        assert dedent(printed) == dedent(outcome)

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
        assert dedent(printed) == dedent(outcome)


class TestRoundRobin:
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
            assert len(d) == len(output)
            assert set(d) == set(output)

        # TODO: Test that order is actually shuffled


### ASSERTIONS:
# There must be exactly one game_state with finished=True

class TestSingleMatch:
    def test_run_match(self):
        config = MagicMock()
        config.rounds = 200
        config.team_spec = lambda x: x
        config.viewer = 'ascii'
        config.filter = 'small'
        config.tournament_log_folder = None

        teams = ["StoppingPlayer", "StoppingPlayer"]
        (state, stdout, stderr) = tournament.run_match(config, teams)
        assert state['team_wins'] == None
        assert state['game_draw'] == True

        config.rounds = 200
        config.team_spec = lambda x: x
        config.viewer = 'ascii'
        teams = ["SmartEatingPlayer", "StoppingPlayer"]
        (state, stdout, stderr) = tournament.run_match(config, teams)
        print(state)
        assert state['team_wins'] == 0
        assert state['game_draw'] == None

        config.rounds = 200
        config.team_spec = lambda x: x
        config.viewer = 'ascii'
        teams = ["StoppingPlayer", "SmartEatingPlayer"]
        (state, stdout, stderr) = tournament.run_match(config, teams)
        assert state['team_wins'] == 1
        assert state['game_draw'] == None

    def test_start_match(self):
        stdout = []

        def mock_print(str="", *args, **kwargs):
            print(str)
            stdout.append(str)

        teams = {
            "first_id": "StoppingPlayer",
            "second_id": "SmartEatingPlayer",
        }

        config = MagicMock()
        config.rounds = 300
        config.team_spec = lambda x: teams[x]
        config.team_name = lambda x: teams[x]
        config.viewer = 'ascii'
        config.filter = 'small'
        config.print = mock_print
        config.tournament_log_folder = None

        team_ids = ["first_id", "first_id"]
        result = tournament.start_match(config, team_ids)
        assert result == False
        assert stdout[-1] == '‘StoppingPlayer’ and ‘StoppingPlayer’ had a draw.'

        team_ids = ["second_id", "first_id"]
        result = tournament.start_match(config, team_ids)
        assert result == "second_id"
        assert stdout[-1] == '‘SmartEatingPlayer’ wins'

        team_ids = ["first_id", "second_id"]
        result = tournament.start_match(config, team_ids)
        assert result == "second_id"
        assert stdout[-1] == '‘SmartEatingPlayer’ wins'


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
        config.tournament_log_folder = None

        result = tournament.start_deathmatch(config, *teams.keys())
        assert result is not None
        assert result in ["first_id", "second_id"]


class TestTournament:
    def test_team_id_check(self):
        with pytest.raises(ValueError):
            tournament.create_team_id(1, 0)
        with pytest.raises(ValueError):
            tournament.create_team_id("#abc", 0)
        with pytest.raises(ValueError):
            tournament.create_team_id("", 0)
        assert tournament.create_team_id(None, 3) == "#3"
        assert tournament.create_team_id("abc", 3) == "abc"

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
                {"id": "group1", "spec": "SmartEatingPlayer", "members": []},
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
        config.tournament_log_folder = None

        # group1 should win
        assert "group1" == tournament.start_match(config, ["group0", "group1"])
        assert "group1" == tournament.start_match(config, ["group1", "group0"])
        assert False == tournament.start_match(config, ["group0", "group0"])

        tournament.present_teams(config)

        state = tournament.State(config)
        rr_ranking = tournament.round1(config, state)

        if config.bonusmatch:
            sorted_ranking = komode.sort_ranks(rr_ranking[:-1]) + [rr_ranking[-1]]
        else:
            sorted_ranking = komode.sort_ranks(rr_ranking)

        winner = tournament.round2(config, sorted_ranking, state)
        assert winner == 'group1'

