import unittest

import pelita
import pytest

print(dir(pelita))
with pelita.utils.with_sys_path('test'):
    import module_player

check_module_cases = [
    ('test/test_pelitagame.py', None),
    ('test/__init__.py', ValueError),
    ('test/', ValueError),
    ('test', ValueError),
    ('doc/source/groupN', None),
    ('doc/source/groupN/__init__.py', ValueError),
    ('doc/source/time', ValueError),
    ]

class TestCheckModule(unittest.TestCase):
    def test_check_module(self):
        for path,result in check_module_cases:
            print(path, result)
            if result is not None:
                with pytest.raises(result):
                    module_player.check_module(path)
            else:
                module_player.check_module(path)
