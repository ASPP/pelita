import pytest
from unittest.mock import MagicMock

import re
from random import Random
from textwrap import dedent

from pelita import tournament
from pelita.tournament import knockout_mode, roundrobin
from pelita.tournament.knockout_mode import Team, Match, Bye

RNG = Random()

def test_match_id():
    assert str(tournament.MatchID()) == 'round1-match01'
    assert str(tournament.MatchID(round=1)) == 'round1-match01'
    assert str(tournament.MatchID(round=2)) == 'round2-match01'
    assert str(tournament.MatchID(round=1, match=1)) == 'round1-match01'
    assert str(tournament.MatchID(round=1, match=2, match_repeat=1)) == 'round1-match02'
    assert str(tournament.MatchID(round=1, match=2, match_repeat=2)) == 'round1-match02-repeat2'

    match_id = tournament.MatchID(round=1, match=2, match_repeat=2)
    match_id.next_round()
    assert match_id == tournament.MatchID(round=2, match=1, match_repeat=1)

    match_id = tournament.MatchID(round=1, match=2, match_repeat=2)
    match_id.next_match()
    assert match_id == tournament.MatchID(round=1, match=3, match_repeat=1)

    match_id = tournament.MatchID(round=1, match=2, match_repeat=2)
    match_id.next_repeat()
    assert match_id == tournament.MatchID(round=1, match=2, match_repeat=3)


class TestKoMode:
    def test_sort_ranks(self):
        sort_ranks = knockout_mode.sort_ranks
        assert sort_ranks([0, 1, 2, 3, 4, 5, 6]) == [0, 5, 1, 4, 2, 3, 6]
        assert sort_ranks([0, 1, 2, 3, 4, 5]) == [0, 5, 1, 4, 2, 3]
        assert sort_ranks([0, 1, 2, 3, 4]) == [0, 3, 1, 2, 4]
        assert sort_ranks([0, 1, 2, 3]) == [0, 3, 1, 2]
        assert sort_ranks([0, 1, 2]) == [0, 1, 2]
        assert sort_ranks([0, 1]) == [0, 1]
        assert sort_ranks([0]) == [0]
        assert sort_ranks([]) == []

        assert sort_ranks([0, 1, 2, 3, 4, 5, 6], bonusmatch=True) == [0, 5, 1, 4, 2, 3, 6]
        assert sort_ranks([0, 1, 2, 3, 4, 5], bonusmatch=True) == [0, 3, 1, 2, 4, 5]
        assert sort_ranks([0, 1, 2, 3, 4], bonusmatch=True) == [0, 3, 1, 2, 4]
        assert sort_ranks([0, 1, 2, 3], bonusmatch=True) == [0, 1, 2, 3]
        assert sort_ranks([0, 1, 2], bonusmatch=True) == [0, 1, 2]
        assert sort_ranks([0, 1], bonusmatch=True) == [0, 1]
        assert sort_ranks([0], bonusmatch=True) == [0]
        assert sort_ranks([], bonusmatch=True) == []


    def test_prepared_matches(self):
        with pytest.raises(ValueError):
            none = knockout_mode.prepare_matches([])
        with pytest.raises(ValueError):
            none = knockout_mode.prepare_matches([], bonusmatch=True)

        single = knockout_mode.prepare_matches([1])
        assert single == knockout_mode.Team(name=1)
        single = knockout_mode.prepare_matches([1], bonusmatch=True)
        assert single == knockout_mode.Team(name=1)

        pair = knockout_mode.prepare_matches([1,2])
        assert pair == Match(t1=Team(name=1), t2=Team(name=2))
        pair = knockout_mode.prepare_matches([1,2], bonusmatch=True)
        assert pair == Match(t1=Team(name=1), t2=Team(name=2))

        triple = knockout_mode.prepare_matches([1,2,3])
        assert triple == Match(t1=Match(t1=Team(name=1), t2=Team(name=2)), t2=Bye(team=Team(name=3)))
        triple = knockout_mode.prepare_matches([1,2,3], bonusmatch=True)
        assert triple == Match(t1=Match(t1=Team(name=1), t2=Team(name=2)), t2=Bye(team=Team(name=3)))

        matches = knockout_mode.prepare_matches([1,2,3,4])
        outcome = Match(t1=Match(t1=Team(name=1), t2=Team(name=4)), t2=Match(t1=Team(name=2), t2=Team(name=3)))
        assert matches == outcome
        matches = knockout_mode.prepare_matches([1,2,3,4], bonusmatch=True)
        outcome = Match(t1=Match(t1=Match(t1=Team(name=1), t2=Team(name=2)), t2=Bye(team=Team(name=3))), t2=Bye(team=Bye(team=Team(name=4))))
        assert matches == outcome

        matches = knockout_mode.prepare_matches([1,2,3,4,5])
        outcome = Match(t1=Match(t1=Match(t1=Team(name=1), t2=Team(name=4)), t2=Match(t1=Team(name=2), t2=Team(name=3))), t2=Bye(team=Bye(team=Team(name=5))))
        assert matches == outcome
        matches = knockout_mode.prepare_matches([1,2,3,4,5], bonusmatch=True)
        outcome = Match(t1=Match(t1=Match(t1=Team(name=1), t2=Team(name=4)), t2=Match(t1=Team(name=2), t2=Team(name=3))), t2=Bye(team=Bye(team=Team(name=5))))
        assert matches == outcome

        matches = knockout_mode.prepare_matches([1,2,3,4,5,6])
        outcome = Match(t1=Match(t1=Match(t1=Team(name=1), t2=Team(name=6)), t2=Match(t1=Team(name=2), t2=Team(name=5))), t2=Bye(team=Match(t1=Team(name=3), t2=Team(name=4))))
        assert matches == outcome
        matches = knockout_mode.prepare_matches([1,2,3,4,5,6], bonusmatch=True)
        outcome = Match(t1=Match(t1=Match(t1=Match(t1=Team(name=1), t2=Team(name=4)), t2=Match(t1=Team(name=2), t2=Team(name=3))), t2=Bye(team=Bye(team=Team(name=5)))), t2=Bye(team=Bye(team=Bye(team=Team(name=6)))))
        assert matches == outcome


@pytest.mark.parametrize('teams, bonusmatch, check_output', [
    ([1, 2, 3, 4, 5], True, """
        1 ┐
          ├─ ??? ┐
        4 ┘      │
                 ├─ ??? ┐
        2 ┐      │      │  ┏━━━━━┓
          ├─ ??? ┘      ├──┨ ??? ┃
        3 ┘             │  ┗━━━━━┛
                        │
        5 ──────────────┘
        """),
    ([1, 2, 3, 4, 5, 6], False, """
        1 ┐
          ├─ ??? ┐
        6 ┘      │
                 ├─ ??? ┐
        2 ┐      │      │
          ├─ ??? ┘      │  ┏━━━━━┓
        5 ┘             ├──┨ ??? ┃
                        │  ┗━━━━━┛
        3 ┐             │
          ├─ ??? ───────┘
        4 ┘
        """),
    ([1, 2, 3, 4, 5, 6], True, """
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
        6 ─────────────────────┘
        """),
])
def test_knockout_output(teams, bonusmatch, check_output):
    matches = knockout_mode.prepare_matches(teams, bonusmatch=bonusmatch)
    printed = knockout_mode.print_knockout(matches)
    # remove the whitespace to the right of the printed lines
    printed = re.sub(r'\s+$', '', printed, flags=re.MULTILINE)
    assert dedent(printed).strip() == dedent(check_output).strip()


class TestRoundRobin:
    def test_all_matches_included(self):
        data = [
            ([], []),
            ([1], []),
            ([1, 2], [(1, 2)]),
            ([1, 2, 3], [(1, 2), (1, 3), (2, 3)]),
            ([1, 2, 3, 4], [(1, 2), (1, 3), (1, 4), (2, 3), (2, 4), (3, 4)]),
            ([0, 1, 2, 3, 4], [(0, 1), (0, 2), (0, 3), (0, 4), (1, 2), (1, 3), (1, 4), (2, 3), (2, 4), (3, 4)])
        ]

        def tuple_sort(t):
            # sort a tuple
            return tuple(sorted(list(t)))

        for input, output in data:
            matchplan = roundrobin.create_matchplan(input, rng=RNG)
            matchplan_sorted = sorted([tuple_sort(x) for x in matchplan])
            output = sorted([tuple_sort(x) for x in output])
            assert matchplan_sorted == output

    @pytest.mark.parametrize('teams',  [
            [0, 1, 2, 3, 4],
            [0, 1, 2, 3, 4, 5],
            [0, 1, 2, 3, 4, 5, 6],
            [0, 1, 2, 3, 4, 5, 6, 7]
        ])
    def test_no_team_plays_two_games_in_a_row(self, teams):
        matches = roundrobin.create_matchplan(teams, rng=RNG)
        prev = {}
        for match in matches:
            current = set(match)
            assert current.isdisjoint(prev)
            prev = current

    @pytest.mark.parametrize('teams',  [
            [0, 1],
            [0, 1, 2],
            [0, 1, 2, 3],
            [0, 1, 2, 3, 4],
            [0, 1, 2, 3, 4, 5],
            [0, 1, 2, 3, 4, 5, 6],
            [0, 1, 2, 3, 4, 5, 6, 7],
        ])
    def test_team_blue_red_are_similar(self, teams):
        # test that each team plays a similar amount as blue and red
        matchplan = roundrobin.create_matchplan(teams, rng=RNG)
        from collections import Counter
        blue_count = Counter()
        red_count = Counter()
        for blue, red in matchplan:
            blue_count[blue] += 1
            red_count[red] += 1
        for team in teams:
            assert -1 <= blue_count[team] - red_count[team] <= 1, matchplan

    @pytest.mark.parametrize('list, fixed, outcome',  [
            ([0], 0, [0]),
            ([0, 1], 0, [0, 1]),
            ([0, 1], 1, [0, 1]),
            ([0, 1, 2], 0, [0, 2, 1]),
            ([0, 1, 2], 1, [2, 1, 0]),
            ([0, 1, 2], 2, [1, 0, 2]),
            ([0, 1, 2, 3], 2, [1, 3, 2, 0]),
            ([0, 1, 2, 3, 4], 3, [1, 2, 4, 3, 0]),
            ([0, 1, 2, 3, 4, 5], 2, [1, 3, 2, 4, 5, 0])
        ])
    def test_rotate_with_fixed(self, list, fixed, outcome):
        assert roundrobin.rotate_with_fixed(list, fixed) == outcome


### ASSERTIONS:
# There must be exactly one game_state with finished=True

class TestSingleMatch:
    def test_play_game_with_config(self):
        config = MagicMock()
        config.rounds = 200
        config.team_spec = lambda x: x
        config.team_group = lambda x: x
        config.viewer = 'ascii'
        config.size = 'small'
        config.tournament_log_folder = None

        teams = ["pelita/player/StoppingPlayer", "pelita/player/StoppingPlayer"]
        (state, stdout, stderr) = tournament.play_game_with_config(config, teams, rng=RNG)
        assert state['whowins'] == 2

        config.rounds = 200
        config.team_spec = lambda x: x
        config.viewer = 'ascii'
        teams = ["pelita/player/SmartEatingPlayer", "pelita/player/StoppingPlayer"]
        (state, stdout, stderr) = tournament.play_game_with_config(config, teams, rng=RNG)
        print(state)
        assert state['whowins'] == 0

        config.rounds = 200
        config.team_spec = lambda x: x
        config.viewer = 'ascii'
        teams = ["pelita/player/StoppingPlayer", "pelita/player/SmartEatingPlayer"]
        (state, stdout, stderr) = tournament.play_game_with_config(config, teams, rng=RNG)
        assert state['whowins'] == 1

    def test_start_match(self):
        stdout = []

        def mock_print(str="", *args, **kwargs):
            print(str)
            stdout.append(str)

        teams = {
            "first_id": "pelita/player/StoppingPlayer",
            "second_id": "pelita/player/SmartEatingPlayer",
        }

        config = MagicMock()
        config.rounds = 300
        config.team_spec = lambda x: teams[x]
        config.team_name = lambda x: teams[x]
        config.team_group = lambda x: x
        config.viewer = 'ascii'
        config.size = 'small'
        config.print = mock_print
        config.tournament_log_folder = None

        team_ids = ["first_id", "first_id"]
        result = tournament.start_match(config, team_ids, rng=RNG)
        assert result == False
        assert stdout[-1] == '‘pelita/player/StoppingPlayer’ and ‘pelita/player/StoppingPlayer’ had a draw.'

        team_ids = ["second_id", "first_id"]
        result = tournament.start_match(config, team_ids, rng=RNG)
        assert result == "second_id"
        assert stdout[-1] == '‘pelita/player/SmartEatingPlayer’ wins'

        team_ids = ["first_id", "second_id"]
        result = tournament.start_match(config, team_ids, rng=RNG)
        assert result == "second_id"
        assert stdout[-1] == '‘pelita/player/SmartEatingPlayer’ wins'


    def test_deathmatch(self):
        stdout = []

        def mock_print(str="", *args, **kwargs):
            stdout.append(str)

        teams = {
            "first_id": "pelita/player/StoppingPlayer",
            "second_id": "pelita/player/StoppingPlayer",
        }

        config = MagicMock()
        config.rounds = 200
        config.teams = teams
        config.team_spec = lambda x: teams[x]
        config.team_name = lambda x: teams[x]
        config.team_group = lambda x: x
        config.viewer = 'ascii'
        config.size = 'small'
        config.print = mock_print
        config.tournament_log_folder = None

        result = tournament.start_deathmatch(config, *teams.keys(), rng=RNG)
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
                {"id": "group0", "spec": "pelita/player/StoppingPlayer", "members": []},
                {"id": "group1", "spec": "pelita/player/SmartEatingPlayer", "members": []},
                {"id": "group2", "spec": "pelita/player/StoppingPlayer", "members": []},
                {"id": "group3", "spec": "pelita/player/StoppingPlayer", "members": []},
                {"id": "group4", "spec": "pelita/player/StoppingPlayer", "members": []},
            ],
            "size": "small",
        }
        config = tournament.Config(c)
        config.print = mock_print
        config.viewer = 'null'
        config.state = None
        config.tournament_log_folder = None

        # group1 should win
        assert "group1" == tournament.start_match(config, ["group0", "group1"], rng=RNG)
        assert "group1" == tournament.start_match(config, ["group1", "group0"], rng=RNG)
        assert False == tournament.start_match(config, ["group0", "group0"], rng=RNG)

        tournament.present_teams(config)

        state = tournament.State(config, rng=RNG)
        rr_ranking = tournament.play_round1(config, state, rng=RNG)

        if config.bonusmatch:
            sorted_ranking = knockout_mode.sort_ranks(rr_ranking[:-1]) + [rr_ranking[-1]]
        else:
            sorted_ranking = knockout_mode.sort_ranks(rr_ranking)

        winner = tournament.play_round2(config, sorted_ranking, state, rng=RNG)
        assert winner == 'group1'

