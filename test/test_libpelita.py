import pytest

import sys

from pelita.simplesetup import ZMQClientError
from pelita import libpelita


class TestLibpelitaUtils:
    def test_firstNN(self):
        assert libpelita.firstNN(None, False, True) == False
        assert libpelita.firstNN(True, False, True) == True
        assert libpelita.firstNN(None, None, True) == True
        assert libpelita.firstNN(None, 2, True) == 2
        assert libpelita.firstNN(None, None, None) == None
        assert libpelita.firstNN() == None

class TestCallPelita:
    def test_call_pelita(self):
        rounds = 200
        viewer = 'ascii'
        filter = 'small'

        teams = ["pelita/player/StoppingPlayer", "pelita/player/StoppingPlayer"]
        (state, stdout, stderr) = libpelita.call_pelita(teams, rounds=rounds, viewer='null', filter=filter, dump=None, seed=None)
        assert state['gameover'] is True
        assert state['whowins'] == 2
        # Quick assert that there is text in stdout
        assert len(stdout.split('\n')) == 6

        teams = ["pelita/player/SmartEatingPlayer", "pelita/player/StoppingPlayer"]
        (state, stdout, stderr) = libpelita.call_pelita(teams, rounds=rounds, viewer=viewer, filter=filter, dump=None, seed=None)
        assert state['gameover'] is True
        assert state['whowins'] == 0

        teams = ["pelita/player/StoppingPlayer", "pelita/player/SmartEatingPlayer"]
        (state, stdout, stderr) = libpelita.call_pelita(teams, rounds=rounds, viewer=viewer, filter=filter, dump=None, seed=None)
        assert state['gameover'] is True
        assert state['whowins'] == 1


def test_check_team_external():
    assert libpelita.check_team("pelita/player/StoppingPlayer") == "Stopping"

def test_check_team_external_fails():
    with pytest.raises(ZMQClientError):
        libpelita.check_team("Unknown Module")

def test_check_team_internal():
    def move(b, s):
        return b.position, s
    assert libpelita.check_team(move) == "local-team (move)"
