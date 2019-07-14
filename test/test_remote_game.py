import pytest

from pathlib import Path
import subprocess
import tempfile
from textwrap import dedent

import pelita.game
from pelita import libpelita
from pelita.player import stopping_player


addr_stopping = 'tcp://127.0.0.1:52301'
addr_food_eater = 'tcp://127.0.0.1:52302'

# Runs the processes for the remote teams
# and sets up `remote_teams` as a pytest fixture
# The processes should automatically terminate then
@pytest.fixture(scope="module")
def remote_teams():
    remote = [libpelita.get_python_process(), '-m', 'pelita.scripts.pelita_player', '--remote']

    remote_stopping = remote + ['pelita/player/StoppingPlayer', addr_stopping]
    remote_food_eater = remote + ['pelita/player/FoodEatingPlayer', addr_food_eater]

#    procs = [subprocess.Popen(args) for args in [remote_stopping, remote_food_eater]]
    teams = [f'remote:{addr_stopping}', f'remote:{addr_food_eater}']
    with libpelita.run_and_terminate_process(remote_stopping):
        with libpelita.run_and_terminate_process(remote_food_eater):
            yield teams


def test_remote_call_pelita(remote_teams):
    res, stdout, stderr = libpelita.call_pelita(remote_teams, rounds=30, filter='small', viewer='null', seed=None)
    assert res['whowins'] == 1
    assert res['fatal_errors'] == [[], []]
    # errors for call_pelita only contains the last thrown error, hence None
    # TODO: should be alligned so that call_pelita and run_game return the same thing
    assert res['errors'] == [None, None]


def test_remote_run_game(remote_teams):
    # TODO: A failure here freezes pytest
    layout = """
        ##########
        #  2  3  #
        #0  ..  1#
        ##########
        """
    state = pelita.game.run_game(remote_teams, max_rounds=30, layout_dict=pelita.layout.parse_layout(layout))
    assert state['whowins'] == 1
    assert state['fatal_errors'] == [[], []]
    assert state['errors'] == [{}, {}]

def test_remote_timeout():
    # We have a slow player that also generates a bad move
    # in its second turn.
    # We need to detect both.

    layout = """
        ##########
        #  2  3  #
        #0  ..  1#
        ##########
        """

    tp = """
    import time
    TEAM_NAME = "500ms timeout"
    def move(b, s):
        if b.round == 1 and b.turn == 1:
            return (-2, 0), s
        time.sleep(0.5)
        return b.position, s
    """
    with tempfile.NamedTemporaryFile('w+', suffix='.py') as f:
        print(dedent(tp), file=f, flush=True)
        timeout_player = f.name

        state = pelita.game.run_game([stopping_player, timeout_player],
                                     max_rounds=8,
                                     layout_dict=pelita.layout.parse_layout(layout),
                                     timeout_length=0.5)

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
        #  2  3  #
        #0  ..  1#
        ##########
        """

    p1 = dedent("""
    import sys
    TEAM_NAME="p1"
    def move(b, s):
        print(f"{b.round} {b.turn} p1", file=sys.stdout)
        print(f"p1err", file=sys.stderr)
        return b.position, s
    """)

    p2 = dedent("""
    import sys
    TEAM_NAME="p2"
    def move(b, s):
        print(f"{b.round} {b.turn} p2", file=sys.stdout)
        print("p2err", file=sys.stderr)
        return b.position, s
    """)
    out_folder = tempfile.TemporaryDirectory()

    with tempfile.NamedTemporaryFile('w+', suffix='.py') as f:
        with tempfile.NamedTemporaryFile('w+', suffix='.py') as g:
            print(p1, file=f, flush=True)
            print(p2, file=g, flush=True)

            state = pelita.game.run_game([f.name, g.name],
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
