import pytest

import pelita

print(dir(pelita))
with pelita.utils.with_sys_path('test'):
    from pelita.scripts.pelita_player import check_module

check_module_cases = [
    ('test/test_pelitagame.py', None),
    ('test/__init__.py', ValueError),
    ('test/', ValueError),
    ('test', ValueError),
    ('doc/source/groupN', None),
    ('doc/source/groupN/__init__.py', ValueError),
    ('doc/source/time', ValueError),
    ]

class TestCheckModule:
    def test_check_module(self):
        for path,result in check_module_cases:
            print(path, result)
            if result is not None:
                with pytest.raises(result):
                    check_module(path)
            else:
                check_module(path)

def test_default_players():
    from pelita.scripts.pelita_main import default_players
    assert [m.__name__ for m in default_players()] == [
        'FoodEatingPlayer',
        'NQRandomPlayer',
        'RandomExplorerPlayer',
        'RandomPlayer',
        'SmartEatingPlayer',
        'SmartRandomPlayer',
    ]
