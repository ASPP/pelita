# -*- coding: utf-8 -*-

import unittest
import sys

class TestColorama(unittest.TestCase):
    def test_colorama_wrapper(self):
        # pretend, we don’t have colorama installed
        sys.modules['colorama']=None
        from pelita.utils.colorama_wrapper import colorama
        test_str = "" + colorama.Fore.MAGENTA + "" + colorama.Fore.RESET
        self.assertEqual(test_str, "")

        del sys.modules['colorama']

