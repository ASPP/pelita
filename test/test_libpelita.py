import pytest

import subprocess
import sys
import tempfile

from pelita.network import ZMQClientError
from pelita.scripts.pelita_tournament import firstNN
from pelita.tournament import call_pelita, check_team

_mswindows = (sys.platform == "win32")


class TestLibpelitaUtils:
    def test_firstNN(self):
        assert firstNN(None, False, True) == False
        assert firstNN(True, False, True) == True
        assert firstNN(None, None, True) == True
        assert firstNN(None, 2, True) == 2
        assert firstNN(None, None, None) == None
        assert firstNN() == None

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
        (state, stdout, stderr) = call_pelita(teams, rounds=rounds, viewer='null', size=size, seed=seed)
        assert state['gameover'] is True
    else:
        with pytest.raises(ValueError):
                call_pelita(teams, rounds=rounds, viewer='null', size=size, seed=seed)


def test_check_team_external():
    assert check_team("pelita/player/StoppingPlayer") == "Stopping Players"

def test_check_team_external_fails():
    with pytest.raises(ZMQClientError):
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

