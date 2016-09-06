import unittest

from pelita import libpelita

class TestLibpelitaUtils(unittest.TestCase):
    def test_firstNN(self):
        self.assertEqual(libpelita.firstNN(None, False, True), False)
        self.assertEqual(libpelita.firstNN(True, False, True), True)
        self.assertEqual(libpelita.firstNN(None, None, True), True)
        self.assertEqual(libpelita.firstNN(None, 2, True), 2)
        self.assertEqual(libpelita.firstNN(None, None, None), None)
        self.assertEqual(libpelita.firstNN(), None)

