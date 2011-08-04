# -*- coding: utf-8 -*-

""" Wrapper file for the colorama terminal coloring tool.
"""

try:
    import colorama
    colorama.init()
except ImportError:
    class _Mock(object):
        def __getattribute__(self, name):
            return ""
    class _Dummy(object):
        Fore = _Mock()
        Back = _Mock()
        Style = _Mock()

    colorama = _Dummy()

