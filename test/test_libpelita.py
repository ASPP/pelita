import re
import subprocess
import sys
import tempfile

import pytest

from pelita.network import RemotePlayerFailure
from pelita.scripts.pelita_tournament import firstNN
from pelita.tournament import call_pelita, check_team

_mswindows = (sys.platform == "win32")


def test_firstNN():
    assert firstNN(None, False, True) is False
    assert firstNN(True, False, True) is True
    assert firstNN(None, None, True) is True
    assert firstNN(None, 2, True) == 2
    assert firstNN(None, None, None) is None
    assert firstNN() is None

def test_call_pelita():
    rounds = 200
    viewer = 'ascii'
    size = 'small'

    teams = ["pelita/player/StoppingPlayer", "pelita/player/StoppingPlayer"]
    (state, stdout, stderr) = call_pelita(teams, rounds=rounds, viewer='null', size=size, seed=None)
    assert state['gameover'] is True
    assert state['whowins'] == 2
    # Quick assert that there is text in stdout
    assert len(stdout.split('\n')) > 0
    assert "Finished" in stdout

    teams = ["pelita/player/SmartEatingPlayer", "pelita/player/StoppingPlayer"]
    (state, stdout, stderr) = call_pelita(teams, rounds=rounds, viewer=viewer, size=size, seed=None)
    assert state['gameover'] is True
    assert state['whowins'] == 0

    teams = ["pelita/player/StoppingPlayer", "pelita/player/SmartEatingPlayer"]
    (state, stdout, stderr) = call_pelita(teams, rounds=rounds, viewer=viewer, size=size, seed=None)
    assert state['gameover'] is True
    assert state['whowins'] == 1


@pytest.mark.parametrize('seed,success', [
        (None, True),
        (0, True),
        (1, True),
        ("1", True),
        ("193294814091830945831093", True),
        ("1.0", False),
        ("daflj", False),
])
def test_bad_seeds(seed, success):
    rounds = 2
    viewer = 'null'
    size = 'small'

    teams = ["pelita/player/StoppingPlayer", "pelita/player/StoppingPlayer"]
    if success:
        (state, _stdout, _stderr) = call_pelita(teams, rounds=rounds, viewer=viewer, size=size, seed=seed)
        assert state['gameover'] is True
    else:
        with pytest.raises(ValueError):
                call_pelita(teams, rounds=rounds, viewer=viewer, size=size, seed=seed)


def test_check_team_external():
    assert check_team("pelita/player/StoppingPlayer") == "Stopping Players"

def test_check_team_external_fails():
    with pytest.raises(RemotePlayerFailure):
        check_team("Unknown Module")

def test_check_team_internal():
    def move(b, s):
        return b.position, s
    assert check_team(move) == "local-team (move)"


@pytest.mark.skipif(_mswindows, reason="NamedTemporaryFiles cannot be used in another process")
def test_write_replay_is_idempotent():
    # TODO: The replay functionality could be added to call_pelita
    # so we don’t have to run the subprocess ourselves
    with tempfile.NamedTemporaryFile() as f:
        with tempfile.NamedTemporaryFile() as g:
            # run a quick game and save the game states to f

            cmd = [sys.executable, '-m', 'pelita.scripts.pelita_main',
                    '--write-replay', f.name,
                    '--size', 'small',
                    '--null']

            subprocess.run(cmd, check=True)

            f.seek(0)
            first_run = f.read()
            # check that we received something
            assert len(first_run) > 0

            # run a replay of f and store in g
            cmd = [sys.executable, '-m', 'pelita.scripts.pelita_main',
                    '--write-replay', g.name,
                    '--replay', f.name,
                    '--null']

            subprocess.run(cmd, check=True)

            g.seek(0)
            second_run = g.read()
            # check that f and g have the same content
            assert first_run == second_run


@pytest.mark.skipif(_mswindows, reason="NamedTemporaryFiles cannot be used in another process")
def test_store_layout():
    # TODO: The store layout functionality could be added to call_pelita
    # so we don’t have to run the subprocess ourselves
    with tempfile.NamedTemporaryFile() as f:
        # run a quick game and save the game states to f

        cmd = [sys.executable, '-m', 'pelita.scripts.pelita_main',
                '--store-layout', f.name,
                '--size', 'small',
                '--seed', '12345',
                '--null']

        subprocess.run(cmd, check=True)

        f.seek(0)
        first_run = f.read()
        # check that we received something and it may be a layout
        assert len(first_run) > 0
        assert first_run[:17] == b"#" * 16 + b"\n"

        # TODO check that the layout can be loaded again

    # Check that the same seed generates the same layout
    with tempfile.NamedTemporaryFile() as g:
        cmd = [sys.executable, '-m', 'pelita.scripts.pelita_main',
                '--store-layout', g.name,
                '--size', 'small',
                '--seed', '12345',
                '--null']

        subprocess.run(cmd, check=True)

        g.seek(0)
        second_run = g.read()
        # check that f and g have the same content
        assert first_run == second_run


def test_random_layout_seed_is_random():
    # NB: Test relies on randomness. It should be EXTREMELY unlikely that this test fails

    # TODO: The store layout functionality could be added to call_pelita
    # so we don’t have to run the subprocess ourselves

    cmd = [sys.executable, '-m', 'pelita.scripts.pelita_main',
            '--store-layout', '-',
            '--size', 'small',
            '--null']

    res = subprocess.run(cmd, check=True, text=True, stdout=subprocess.PIPE)
    lines = res.stdout.split('\n')
    seed0 = re.match(r'.+--seed (\d+)', lines[0]).group(1)

    # seed can be converted to a number
    assert int(seed0) >= 0

    res = subprocess.run(cmd, check=True, text=True, stdout=subprocess.PIPE)
    lines = res.stdout.split('\n')
    seed1 = re.match(r'.+--seed (\d+)', lines[0]).group(1)

    # seed can be converted to a number
    assert int(seed1) >= 0

    assert seed0 != seed1


def test_random_layout_seed_is_stable():
    # TODO: The store layout functionality could be added to call_pelita
    # so we don’t have to run the subprocess ourselves

    cmd = [sys.executable, '-m', 'pelita.scripts.pelita_main',
            '--store-layout', '-',
            '--size', 'small',
            '--null']

    res = subprocess.run(cmd, check=True, text=True, stdout=subprocess.PIPE)
    lines = res.stdout.split('\n')
    seed = re.match(r'.+--seed (\d+)', lines[0]).group(1)

    layout_str = lines[1:]
    # check that we received something and it may be a layout
    assert layout_str[0] == "#" * 16

    # Check that the same seed generates the same layout
    cmd = [sys.executable, '-m', 'pelita.scripts.pelita_main',
            '--store-layout', '-',
            '--size', 'small',
            '--seed', seed,
            '--null']

    res = subprocess.run(cmd, check=True, text=True, stdout=subprocess.PIPE)
    assert res.stdout.split('\n') == layout_str
