from pelita import libpelita

class TestLibpelitaUtils:
    def test_firstNN(self):
        assert libpelita.firstNN(None, False, True) == False
        assert libpelita.firstNN(True, False, True) == True
        assert libpelita.firstNN(None, None, True) == True
        assert libpelita.firstNN(None, 2, True) == 2
        assert libpelita.firstNN(None, None, None) == None
        assert libpelita.firstNN() == None

