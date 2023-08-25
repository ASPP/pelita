import pytest

import os
from pathlib import Path
import random
import sys
import tempfile
from textwrap import dedent

import pelita.game
from pelita.player import stopping_player
from pelita.tournament import call_pelita, run_and_terminate_process

_mswindows = (sys.platform == "win32")

FIXTURE_DIR = Path(__file__).parent.resolve() / 'testplayers'


# Runs the processes for the remote teams
# and sets up `remote_teams` as a pytest fixture
# The processes should automatically terminate then
# also, listens on different ports each time, to avoid collisions and dead
# locks
RNG = random.Random()

@pytest.fixture(scope="module")
def remote_teams():
    # get random port numbers within the range of dynamic ports
    port_stopping = RNG.randint(49153,65534)
    port_food_eater = port_stopping+1

    addr_stopping = f'tcp://127.0.0.1:{port_stopping}'
    addr_food_eater = f'tcp://127.0.0.1:{port_food_eater}'
    remote = [sys.executable, '-m', 'pelita.scripts.pelita_player', '--remote']

    remote_stopping = remote + ['pelita/player/StoppingPlayer', addr_stopping ]
    remote_food_eater = remote + ['pelita/player/FoodEatingPlayer', addr_food_eater]

    teams = [f'remote:{addr_stopping}', f'remote:{addr_food_eater}']
    with run_and_terminate_process(remote_stopping):
        with run_and_terminate_process(remote_food_eater):
            yield teams


def test_remote_call_pelita(remote_teams):
    res, stdout, stderr = call_pelita(remote_teams, rounds=30, size='small', viewer='null', seed='1')
    assert res['whowins'] == 1
    assert res['fatal_errors'] == [[], []]
    # errors for call_pelita only contains the last thrown error, hence None
    # TODO: should be aligned so that call_pelita and run_game return the same thing
    assert res['errors'] == [None, None]


def test_remote_run_game(remote_teams):
    # TODO: A failure here freezes pytest
    layout = """
        ##########
        #  b  y  #
        #a  ..  x#
        ##########
        """
    state = pelita.game.run_game(remote_teams, max_rounds=30, layout_dict=pelita.layout.parse_layout(layout))
    assert state['whowins'] == 1
    assert state['fatal_errors'] == [[], []]
    assert state['errors'] == [{}, {}]


@pytest.mark.skipif(_mswindows, reason="NamedTemporaryFiles cannot be used in another process")
@pytest.mark.xfail(reason="TODO: Fails in CI for macOS. Unclear why.")
def test_remote_timeout():
    # We have a slow player that also generates a bad move
    # in its second turn.
    # We need to detect both.
    # To avoid timing issues, the blue player will also need to be a bit slower

    layout = """
        ##########
        #  b  y  #
        #a  ..  x#
        ##########
        """

    blue = FIXTURE_DIR / 'remote_timeout_blue.py'
    red = FIXTURE_DIR / 'remote_timeout_red.py'

    state = pelita.game.run_game([str(blue), str(red)],
                                 max_rounds=8,
                                 layout_dict=pelita.layout.parse_layout(layout),
                                 timeout_length=0.4)

    assert state['whowins'] == 0
    assert state['fatal_errors'] == [[], []]
    assert state['errors'] == [{},
        {(1, 1): {'description': '', 'type': 'PlayerTimeout'},
        (1, 3): {'bot_position': (-2, 0), 'reason': 'illegal move'},
        (2, 1): {'description': '', 'type': 'PlayerTimeout'},
        (2, 3): {'description': '', 'type': 'PlayerTimeout'},
        (3, 1): {'description': '', 'type': 'PlayerTimeout'}}]


@pytest.mark.skipif(_mswindows, reason="NamedTemporaryFiles cannot be used in another process")
def test_remote_dumps_are_written():
    layout = """
        ##########
        #  b  y  #
        #a  ..  x#
        ##########
        """


    blue = FIXTURE_DIR / 'remote_dumps_are_written_blue.py'
    red = FIXTURE_DIR / 'remote_dumps_are_written_red.py'

    out_folder = tempfile.TemporaryDirectory()

    state = pelita.game.run_game([str(blue), str(red)],
                                 max_rounds=2,
                                 layout_dict=pelita.layout.parse_layout(layout),
                                 store_output=out_folder.name)

    assert state['whowins'] == 2
    assert state['fatal_errors'] == [[], []]
    assert state['errors'] == [{}, {}]

    path = Path(out_folder.name)
    blue_lines = (path / 'blue.out').read_text().split('\n')
    red_lines = (path / 'red.out').read_text().split('\n')
    # The first line contains the welcome message 'blue team 'path' -> 'name''
    assert 'blue team' in blue_lines[0]
    assert 'red team' in red_lines[0]
    # now check what has been printed
    assert blue_lines[1:] == ['1 0 p1', '1 1 p1', '2 0 p1', '2 1 p1', '']
    assert red_lines[1:] == ['1 0 p2', '1 1 p2', '2 0 p2', '2 1 p2', '']

    assert (path / 'blue.err').read_text() == 'p1err\np1err\np1err\np1err\n'
    assert (path / 'red.err').read_text() == 'p2err\np2err\np2err\np2err\n'


@pytest.mark.skipif(_mswindows, reason="NamedTemporaryFiles cannot be used in another process")
@pytest.mark.parametrize("failing_team", [0, 1])
def test_remote_dumps_with_failure(failing_team):
    layout = """
        ##########
        #  b  y  #
        #a  ..  x#
        ##########
        """

    failing_player = FIXTURE_DIR / 'remote_dumps_with_failure_bad.py'
    good_player = FIXTURE_DIR / 'remote_dumps_with_failure_good.py'

    out_folder = tempfile.TemporaryDirectory()

    if failing_team == 0:
        teams = [str(failing_player), str(good_player)]
    elif failing_team == 1:
        teams = [str(good_player), str(failing_player)]

    state = pelita.game.run_game(teams,
                                 max_rounds=2,
                                 layout_dict=pelita.layout.parse_layout(layout),
                                 store_output=out_folder.name)

    assert state['whowins'] == 1 - failing_team
    # when team 1 fails, it’s turn will be 1
    if failing_team == 0:
        fail_turn = 0
    elif failing_team == 1:
        fail_turn = 1
    assert state['fatal_errors'][failing_team][0] == {'type': 'FatalException',
                                           'description': 'Exception in client (ZeroDivisionError): division by zero',
                                           'turn': fail_turn,
                                           'round': 2}
    assert state['fatal_errors'][1 - failing_team] == []
    assert state['errors'] == [{}, {}]

    path = Path(out_folder.name)

    # stdout is still the same for both teams

    blue_lines = (path / 'blue.out').read_text().split('\n')
    red_lines = (path / 'red.out').read_text().split('\n')
    # The first line contains the welcome message 'blue team 'path' -> 'name''
    assert 'blue team' in blue_lines[0]
    assert 'red team' in red_lines[0]
    # now check what has been printed
    assert blue_lines[1:] == ['']
    assert red_lines[1:] == ['']

    blue_err = (path / 'blue.err').read_text()
    red_err = (path / 'red.err').read_text()

    if failing_team == 0:
        fail_err = blue_err
        good_err = red_err
    elif failing_team == 1:
        fail_err = red_err
        good_err = blue_err

    # Error is of the form:
    # Traceback (most recent call last):
    #   File ".../pelita/player/team.py", line 125, in get_move
    #     res = self._team_move(team[me.bot_turn], self._state)
    #   File "......", line 7, in move
    #     0 / 0
    # ZeroDivisionError: division by zero
    # -- empty line (index -1)

    assert "Traceback (most recent call last):" in fail_err
    assert "0 / 0" in fail_err
    assert "ZeroDivisionError: division by zero" in fail_err

    # No errors for red
    assert good_err == ""
