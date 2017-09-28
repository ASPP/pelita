import pytest

import subprocess

import pelita
from pelita import libpelita
from pelita.simplesetup import SimpleServer

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


import atexit

def terminate_and_wait(proc):
    proc.terminate()
    try:
        proc.wait(3)
    except subprocess.TimeoutExpired:
        proc.kill()

def Popen_autokill(args):
    # we need to autokill in case of errors
    p = subprocess.Popen(args)
    atexit.register((lambda p: lambda: terminate_and_wait(p))(p))
    return p

def test_remote_game():
    remote = [libpelita.get_python_process(), '-m', 'pelita.scripts.pelita_player', '--remote']
    remote_stopping = remote + ['StoppingPlayer', 'tcp://127.0.0.1:52301']
    remote_food_eater = remote + ['FoodEatingPlayer', 'tcp://127.0.0.1:52302']

    remote_procs = [Popen_autokill(args) for args in [remote_stopping, remote_food_eater]]

    layout = """
        ##########
        #        #
        #0  ..  1#
        ##########
        """
    server = SimpleServer(layout_string=layout, rounds=5, players=2,
                          bind_addrs=['remote:tcp://127.0.0.1:52301', 'remote:tcp://127.0.0.1:52302'])

    server.run()
    server.shutdown()

    assert server.game_master.game_state['team_wins'] == 1

    server = SimpleServer(layout_string=layout, rounds=5, players=2,
                          bind_addrs=['remote:tcp://127.0.0.1:52302', 'remote:tcp://127.0.0.1:52301'])

    server.run()
    server.shutdown()

    assert server.game_master.game_state['team_wins'] == 0

    server = SimpleServer(layout_string=layout, rounds=5, players=2,
                          bind_addrs=['remote:tcp://127.0.0.1:52301', 'remote:tcp://127.0.0.1:52302'])

    server.run()
    server.shutdown()

    assert server.game_master.game_state['team_wins'] == 1

    # terminate processes
    [p.terminate() for p in remote_procs]
    for p in remote_procs:
        assert p.wait(2) is not None
