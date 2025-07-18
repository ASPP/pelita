import re
from random import Random
from textwrap import dedent
from unittest.mock import MagicMock

import pytest

from pelita import tournament
from pelita.tournament import knockout_mode, roundrobin
from pelita.tournament.knockout_mode import Bye, Match, Team

RNG = Random()

@pytest.mark.parametrize('teams, output', [
    ([1], 1),
    ([1, 2], [1, 2]),
    ([1, 2, 3, 4], [[1, 4], [2, 3]]),
    ([1, 2, 3, 4, 5], [[[1, None], [4, 5]], [[2, None], [3, None]]]),
    ([1, 2, 3, 4, 5, 6, 7, 8], [[[1, 8], [4, 5]], [[2, 7], [3, 6]]]),
    (list(range(1, 17)),
       [[[[1, 16], [8, 9]], [[4, 13], [5, 12]]],
        [[[2, 15], [7, 10]], [[3, 14], [6, 11]]]]
    )
])
def test_build_bracket(teams, output):
    assert knockout_mode.build_bracket(teams) == output


@pytest.mark.parametrize('teams, output', [
    ([1], Team(name=1)),
    ([1, 2], Match(t1=Team(name=1), t2=Team(name=2))),
    ([1, 2, 3, 4],
     Match(t1=Match(t1=Team(name=1), t2=Team(name=4)),
           t2=Match(t1=Team(name=2), t2=Team(name=3)))
    ),
    ([1, 2, 3, 4, 5],
     Match(t1=Match(t1=Bye(team=Team(name=1)), t2=Match(t1=Team(name=4), t2=Team(name=5))),
           t2=Match(t1=Bye(team=Team(name=2)), t2=Bye(team=Team(name=3))))
    ),
    ([1, 2, 3, 4, 5, 6, 7, 8],
     Match(t1=Match(t1=Match(t1=Team(name=1), t2=Team(name=8)), t2=Match(t1=Team(name=4), t2=Team(name=5))),
           t2=Match(t1=Match(t1=Team(name=2), t2=Team(name=7)), t2=Match(t1=Team(name=3), t2=Team(name=6))))
    ),
])
def test_build_match_tree(teams, output):
    bracket = knockout_mode.build_bracket(teams)
    assert knockout_mode.build_match_tree(bracket) == output

@pytest.mark.parametrize('tree, is_balanced, tree_depth', [
    (Team(name=1), True, 1),
    (Match(t1=Bye(team=Team(name=1)), t2=Match(t1=Team(name=4), t2=Team(name=5))), True, 3),
    (Match(t1=Match(t1=Bye(team=Team(name=1)), t2=Match(t1=Team(name=4), t2=Team(name=5))),
           t2=Match(t1=Bye(team=Team(name=2)), t2=Bye(team=Team(name=3)))), True, 4),
    (Match(t1=Team(name=1), t2=Match(t1=Team(name=4), t2=Team(name=5))), False, 3),
    (Match(t1=Bye(team=Team(name=1)), t2=Team(name=5)), False, 3),
    (Match(t1=Match(t1=Team(name=1), t2=Team(name=4)),
           t2=Match(t1=Team(name=2), t2=Team(name=3))), True, 3),
    # unbalanced subtrees
    (Match(t1=Match(t1=Team(name=1), t2=Bye(team=Team(name=4))),
           t2=Match(t1=Team(name=2), t2=Bye(team=Team(name=3)))), False, 4)
])
def test_is_balanced(tree, is_balanced, tree_depth):
    assert knockout_mode.is_balanced(tree) == is_balanced
    assert knockout_mode.tree_depth(tree) == tree_depth

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

@pytest.mark.parametrize('teams, bonusmatch, output', [
    ([], False, None),
    ([], True, None),
    ([1], False, Team(name=1)),
    ([1], True, Team(name=1)),
    ([1, 2], False, Match(t1=Team(name=1), t2=Team(name=2))),
    ([1, 2], True, Match(t1=Team(name=1), t2=Team(name=2))),
    ([1, 2, 3], False, Match(t1=Bye(team=Team(name=1)), t2=Match(t1=Team(name=2), t2=Team(name=3)))),
    ([1, 2, 3], True, Match(t1=Match(t1=Team(name=1), t2=Team(name=2)), t2=Bye(team=Team(name=3)))),
    ([1, 2, 3, 4], False,
     Match(t1=Match(t1=Team(name=1), t2=Team(name=4)),
           t2=Match(t1=Team(name=2), t2=Team(name=3)))
    ),
    ([1, 2, 3, 4], True,
     Match(Match(t1=Bye(team=Team(name=1)), t2=Match(t1=Team(name=2), t2=Team(name=3))),
           t2=Bye(team=Bye(team=Team(name=4))))
    ),
    ([1, 2, 3, 4, 5], False,
     Match(t1=Match(t1=Bye(team=Team(name=1)), t2=Match(t1=Team(name=4), t2=Team(name=5))),
           t2=Match(t1=Bye(team=Team(name=2)), t2=Bye(team=Team(name=3))))
    ),
    ([1, 2, 3, 4, 5], True,
     Match(t1=Match(t1=Match(t1=Team(name=1), t2=Team(name=4)), t2=Match(t1=Team(name=2), t2=Team(name=3))),
           t2=Bye(team=Bye(team=Team(name=5))))
    ),
    ([1, 2, 3, 4, 5, 6], False,
     Match(t1=Match(t1=Bye(team=Team(name=1)), t2=Match(t1=Team(name=4), t2=Team(name=5))),
           t2=Match(t1=Bye(team=Team(name=2)), t2=Match(t1=Team(name=3), t2=Team(name=6))))
    ),
    ([1, 2, 3, 4, 5, 6], True,
     Match(t1=Match(t1=Match(t1=Bye(team=Team(name=1)), t2=Match(t1=Team(name=4), t2=Team(name=5))), t2=Match(t1=Bye(team=Team(name=2)), t2=Bye(team=Team(name=3)))),
           t2=Bye(team=Bye(team=Bye(team=Team(name=6)))))
    ),
])
def test_prepare_matches(teams, bonusmatch, output):
    if output:
        assert knockout_mode.prepare_matches(teams, bonusmatch) == output
    else:
        with pytest.raises(ValueError):
            _match_tree = knockout_mode.prepare_matches(teams, bonusmatch)

@pytest.mark.parametrize('teams, bonusmatch, check_output', [
    ([1, 2, 3], False, """
        1 ───────┐  ┏━━━━━┓
                 ├──┨ ??? ┃
        2 ┐      │  ┗━━━━━┛
          ├─ ??? ┘
        3 ┘
        """),
    ([1, 2, 3], True, """
        1 ┐
          ├─ ??? ┐  ┏━━━━━┓
        2 ┘      ├──┨ ??? ┃
                 │  ┗━━━━━┛
        3 ───────┘
        """),
    ([1, 2, 3, 4], False, """
        1 ┐
          ├─ ??? ┐
        4 ┘      │  ┏━━━━━┓
                 ├──┨ ??? ┃
        2 ┐      │  ┗━━━━━┛
          ├─ ??? ┘
        3 ┘
        """),
    ([1, 2, 3, 4], True, """
        1 ───────┐
                 ├─ ??? ┐
        2 ┐      │      │  ┏━━━━━┓
          ├─ ??? ┘      ├──┨ ??? ┃
        3 ┘             │  ┗━━━━━┛
                        │
        4 ──────────────┘
        """),
    ([1, 2, 3, 4, 5], False, """
        1 ───────┐
                 ├─ ??? ┐
        4 ┐      │      │
          ├─ ??? ┘      │  ┏━━━━━┓
        5 ┘             ├──┨ ??? ┃
                        │  ┗━━━━━┛
        2 ───────┐      │
                 ├─ ??? ┘
        3 ───────┘
        """),
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
        1 ───────┐
                 ├─ ??? ┐
        4 ┐      │      │
          ├─ ??? ┘      │  ┏━━━━━┓
        5 ┘             ├──┨ ??? ┃
                        │  ┗━━━━━┛
        2 ───────┐      │
                 ├─ ??? ┘
        3 ┐      │
          ├─ ??? ┘
        6 ┘
        """),
    ([1, 2, 3, 4, 5, 6], True, """
        1 ───────┐
                 ├─ ??? ┐
        4 ┐      │      │
          ├─ ??? ┘      │
        5 ┘             ├─ ??? ┐
                        │      │
        2 ───────┐      │      │  ┏━━━━━┓
                 ├─ ??? ┘      ├──┨ ??? ┃
        3 ───────┘             │  ┗━━━━━┛
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
        assert result is False
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
        assert tournament.start_match(config, ["group0", "group0"], rng=RNG) is False

        tournament.present_teams(config)

        state = tournament.State(config, rng=RNG)
        rr_ranking = tournament.play_round1(config, state, rng=RNG)

        winner = tournament.play_round2(config, rr_ranking, state, rng=RNG)
        assert winner == 'group1'
