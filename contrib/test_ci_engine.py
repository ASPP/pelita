import pytest

import ci_engine


@pytest.fixture
def db_wrapper():
    wrapper = ci_engine.DB_Wrapper(':memory:')
    wrapper.create_tables()
    return wrapper

"""Tests for the DB_Wrapper class."""

def test_foreign_keys_enabled(db_wrapper):
    result = db_wrapper.cursor.execute("PRAGMA foreign_keys;").fetchone()
    assert result[0] == 1

def test_add_player(db_wrapper):
    db_wrapper.add_player('p1', 'h1')
    db_wrapper.add_player('p2', 'h2')
    with pytest.raises(ValueError):
        db_wrapper.add_player('p1', 'h1')
    players = sorted(db_wrapper.get_players())
    assert players == ['p1', 'p2']

def test_remove_player(db_wrapper):
    db_wrapper.add_player('p1', 'h1')
    db_wrapper.add_player('p2', 'h2')
    db_wrapper.add_player('p3', 'h3')
    db_wrapper.add_gameresult('p1', 'p2', 0, '{}', '', '')
    db_wrapper.add_gameresult('p2', 'p1', 0, '{}', '', '')
    db_wrapper.add_gameresult('p2', 'p3', 0, '{}', '', '')
    # player2 has three games
    assert len(db_wrapper.get_results('p2')) == 3
    db_wrapper.remove_player('p1')
    # player 1 should have no game results
    assert db_wrapper.get_results('p1') == []
    # after removing all games of player one, player2 should have 1
    # game
    assert len(db_wrapper.get_results('p2')) == 1
    # player 3 should be untouched
    assert len(db_wrapper.get_results('p3')) == 1

def test_add_remove_weirdly_named_player(db_wrapper):
    stupid_names = [
        "Little'",
        'Bobby"',
        "таблицы",
    ]

    for name in stupid_names:
        db_wrapper.add_player(name, name)
        db_wrapper.remove_player(name)

def test_get_players(db_wrapper):
    players = ['p1', 'p2', 'p3']
    for p in players:
        db_wrapper.add_player(p, 'h')
    players2 = sorted(db_wrapper.get_players())
    assert players == players2

def test_get_results(db_wrapper):
    db_wrapper.add_player('p1', 'h1')
    db_wrapper.add_player('p2', 'h2')
    # empty list if no results are available
    assert db_wrapper.get_results('p1') == []
    db_wrapper.add_gameresult('p1', 'p2', 0, '{}', '', '')
    result = db_wrapper.get_results('p1')[0]
    # check for correct values
    assert result[0] == 'p1'
    assert result[1] == 'p2'
    assert result[2] == 0
    db_wrapper.add_gameresult('p2', 'p1', 0, '{}', '', '')
    # check for correct number of results
    results = db_wrapper.get_results('p1')
    assert len(results) == 2

def test_get_player_hash(db_wrapper):
    db_wrapper.add_player('p1', 'h1')
    db_wrapper.add_player('p2', 'h2')
    with pytest.raises(ValueError):
        db_wrapper.get_player_hash('p0')
    assert db_wrapper.get_player_hash('p1') == 'h1'
    assert db_wrapper.get_player_hash('p2') == 'h2'

def test_get_team_name(db_wrapper):
    db_wrapper.add_player('p1', 'h1')
    db_wrapper.add_player('p2', 'h2')
    db_wrapper.add_team_name('p1', 'tn1')
    db_wrapper.add_team_name('p2', 'tn2')
    db_wrapper.add_team_name('p2', 'tn3') # check that override works
    with pytest.raises(ValueError):
        db_wrapper.get_team_name('p0')
    assert db_wrapper.get_team_name('p1') == 'tn1'
    assert db_wrapper.get_team_name('p2') == 'tn3'

def test_wins_losses(db_wrapper):
    db_wrapper.add_player('p1', 'h1')
    db_wrapper.add_player('p2', 'h2')
    db_wrapper.add_player('p3', 'h3')
    db_wrapper.add_gameresult('p1', 'p2', 0, "{}", "", "")
    assert db_wrapper.get_wins_losses() == [
        ('p1', 'p2', 1, 0, 0),
        ('p2', 'p1', 0, 1, 0)
    ]
    db_wrapper.add_gameresult('p1', 'p2', -1, "{}", "", "")
    assert db_wrapper.get_wins_losses() == [
        ('p1', 'p2', 1, 0, 1),
        ('p2', 'p1', 0, 1, 1)
    ]
    db_wrapper.add_gameresult('p2', 'p1', 1, "{}", "", "")
    assert db_wrapper.get_wins_losses() == [
        ('p1', 'p2', 2, 0, 1),
        ('p2', 'p1', 0, 2, 1)
    ]
    db_wrapper.add_gameresult('p3', 'p1', 1, "{}", "", "")
    assert db_wrapper.get_wins_losses() == [
        ('p1', 'p2', 2, 0, 1),
        ('p1', 'p3', 1, 0, 0),
        ('p2', 'p1', 0, 2, 1),
        ('p3', 'p1', 0, 1, 0)
    ]

    assert db_wrapper.get_wins_losses('p1') == [
        ('p1', 'p2', 2, 0, 1),
        ('p1', 'p3', 1, 0, 0),
    ]

    assert db_wrapper.get_results('p1') == [
        ('p1', 'p2', 0),
        ('p1', 'p2', -1),
        ('p2', 'p1', 1),
        ('p3', 'p1', 1)
    ]

    assert db_wrapper.get_game_count('p1') == 4
    assert db_wrapper.get_game_count('p2') == 3
    assert db_wrapper.get_game_count('p1', 'p2') == 3
    assert db_wrapper.get_game_count('p2', 'p1') == 3
    assert db_wrapper.get_game_count('p3', 'p1') == 1
