import pytest

import sys

from pelita import libpelita

class TestLibpelitaUtils:
    def test_firstNN(self):
        assert libpelita.firstNN(None, False, True) == False
        assert libpelita.firstNN(True, False, True) == True
        assert libpelita.firstNN(None, None, True) == True
        assert libpelita.firstNN(None, 2, True) == 2
        assert libpelita.firstNN(None, None, None) == None
        assert libpelita.firstNN() == None

@pytest.mark.skipif(sys.platform == 'win32', reason="does not run on windows")
class TestCallPelita:
    def test_call_pelita(self):
        rounds = 200
        viewer = 'ascii'
        filter = 'small'

        teams = ["StoppingPlayer", "StoppingPlayer"]
        (state, stdout, stderr) = libpelita.call_pelita(teams, rounds=rounds, viewer=viewer, filter=filter, dump=None, seed=None)
        assert state['team_wins'] is None
        assert state['game_draw'] is True

        teams = ["SmartEatingPlayer", "StoppingPlayer"]
        (state, stdout, stderr) = libpelita.call_pelita(teams, rounds=rounds, viewer=viewer, filter=filter, dump=None, seed=None)
        assert state['team_wins'] == 0
        assert state['game_draw'] is None

        teams = ["StoppingPlayer", "SmartEatingPlayer"]
        (state, stdout, stderr) = libpelita.call_pelita(teams, rounds=rounds, viewer=viewer, filter=filter, dump=None, seed=None)
        assert state['team_wins'] == 1
        assert state['game_draw'] is None

