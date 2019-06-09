import pytest

import subprocess

import pelita.game
from pelita import libpelita


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
    res, stdout, stderr = libpelita.call_pelita(remote_teams, rounds=30, filter='small', viewer='null', dump=None, seed=None)
    assert res['whowins'] == 1
    assert res['fatal_errors'] == [[], []]
    assert res['errors'] == [[], []]


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
    assert state['errors'] == [[], []]
