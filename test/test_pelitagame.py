import unittest
import pelita
with pelita.utils.with_sys_path('test'):
    import pelitagame

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
                self.assertRaises(result, pelitagame.check_module, path)
            else:
                pelitagame.check_module(path)
