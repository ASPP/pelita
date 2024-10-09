import pytest

import sys
import tempfile
from pathlib import Path
from random import Random


import pelita.game
from pelita.tournament import call_pelita, run_and_terminate_process

_mswindows = (sys.platform == "win32")

FIXTURE_DIR = Path(__file__).parent.resolve() / 'fixtures'


# Runs the processes for the remote teams
# and sets up `remote_teams` as a pytest fixture
# The processes should automatically terminate then
# also, listens on different ports each time, to avoid collisions and dead
# locks
RNG = Random()

@pytest.fixture(scope="module")
def remote_teams():
    # get random port numbers within the range of dynamic ports
    port_stopping = RNG.randint(49153,65534)
    port_food_eater = port_stopping+1

    addr_stopping = "127.0.0.1"
    addr_food_eater = "127.0.0.1"
    remote = [sys.executable, '-m', 'pelita.scripts.pelita_server', 'remote-server', '--address', '127.0.0.1']

    remote_stopping = remote + ['--port', str(port_stopping), '--team', 'pelita/player/StoppingPlayer']
    remote_food_eater = remote + ['--port', str(port_food_eater), '--team', 'pelita/player/FoodEatingPlayer']

    teams = [f'pelita://127.0.0.1:{port_stopping}/Stopping_Players', f'pelita://127.0.0.1:{port_food_eater}/Food_Eating_Players']
    with run_and_terminate_process(remote_stopping):
        with run_and_terminate_process(remote_food_eater):
            yield teams


def test_remote_call_pelita(remote_teams):
    res, stdout, stderr = call_pelita(remote_teams, rounds=30, size='small', viewer='null', seed='2')
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
    print(f"Using temporary folder to store the output: {out_folder}")

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
    # now check what has been printed
    assert blue_lines == ['1 0 p1', '1 1 p1', '2 0 p1', '2 1 p1', '']
    assert red_lines == ['1 0 p2', '1 1 p2', '2 0 p2', '2 1 p2', '']

    assert (path / 'blue.err').read_text() == 'p1err\np1err\np1err\np1err\n'
    assert (path / 'red.err').read_text() == 'p2err\np2err\np2err\np2err\n'


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
    print(f"Using temporary folder to store the output: {out_folder}")

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
    assert blue_lines == ['']
    assert red_lines == ['']

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


@pytest.mark.parametrize("player_name,is_setup_error,error_type", [
    ['player_move_bad_type', False, 'ValueError'],
    ['player_move_bad_value', False, 'ValueError'],
    ['player_move_division_by_zero', False, 'ZeroDivisionError'],
    ['player_move_import_error', False, 'ModuleNotFoundError'],
    ['player_move_type_error', False, 'TypeError'],
    ['player_move_value_error', False, 'ValueError'],
    ['player_import_error', True, 'ModuleNotFoundError'],
    ['player_move_bad_args', False, 'TypeError'],
    ['player_move_bad_args_too_many', False, 'TypeError'],
    ['player_no_move', True, 'AttributeError'],
    ['player_no_name', True, 'AttributeError'],
    ['player_syntax_error', True, 'SyntaxError'],
])
def test_remote_move_failures(player_name, is_setup_error, error_type):
    layout = """
        ##########
        #  b  y  #
        #a  ..  x#
        ##########
        """

    failing_player = FIXTURE_DIR / player_name
    good_player = FIXTURE_DIR / 'remote_dumps_with_failure_good.py'

    if is_setup_error:
        state = pelita.game.run_game([str(failing_player), str(good_player)],
                                      max_rounds=2,
                                      layout_dict=pelita.layout.parse_layout(layout))

        assert state['whowins'] == 1

        assert state['fatal_errors'][0][0]['type'] == 'PlayerDisconnected'
        assert 'Could not load' in state['fatal_errors'][0][0]['description']
        assert error_type in state['fatal_errors'][0][0]['description']
        assert state['fatal_errors'][0][0]['turn'] == 0
        assert state['fatal_errors'][0][0]['round'] == None
        assert state['fatal_errors'][1] == []
        assert state['errors'] == [{}, {}]

    else:
        state = pelita.game.run_game([str(failing_player), str(good_player)],
                                      max_rounds=2,
                                      layout_dict=pelita.layout.parse_layout(layout))

        assert state['whowins'] == 1

        assert state['fatal_errors'][0][0]['type'] == 'FatalException'
        assert f'Exception in client ({error_type})' in state['fatal_errors'][0][0]['description']
        assert state['fatal_errors'][0][0]['turn'] == 0
        assert state['fatal_errors'][0][0]['round'] == 1
        assert state['fatal_errors'][1] == []
        assert state['errors'] == [{}, {}]
