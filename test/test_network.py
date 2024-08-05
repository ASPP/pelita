import pytest

import uuid
import sys

import zmq

from pelita.network import bind_socket
from pelita.team import make_team
from pelita.scripts.pelita_player import player_handle_request

_mswindows = (sys.platform == "win32")


@pytest.fixture(scope="module")
def zmq_context():
    context = zmq.Context()
    yield context
    context.destroy()

@pytest.mark.skipif(_mswindows, reason="No IPC sockets on Windows.")
def test_bind_socket_success(zmq_context):
    socket = zmq_context.socket(zmq.PUB)
    address = "ipc:///tmp/pelita-test-bind-socket-%s" % uuid.uuid4()
    bind_socket(socket, address)

def test_bind_socket_fail(zmq_context):
    socket = zmq_context.socket(zmq.PUB)
    with pytest.raises(zmq.ZMQError):
        bind_socket(socket, "bad-address", '--publish')
    socket.close()


def test_simpleclient(zmq_context):
    res = []
    def stopping(bot, state):
        print(bot)
        res.append(True)
        print(res)
        return bot.position

    sock = zmq_context.socket(zmq.PAIR)
    port = sock.bind_to_random_port('tcp://127.0.0.1')

    team, _ = make_team(stopping, team_name='test stopping player')
    client_sock = zmq_context.socket(zmq.PAIR)
    client_sock.connect(f'tcp://127.0.0.1:{port}')

    # Faking some data
    _uuid = uuid.uuid4().__str__()
    set_initial = {
        '__uuid__': _uuid,
        '__action__': "set_initial",
        '__data__': {
            'team_id': 0,
            'game_state': {
                'seed': 0,
                'walls': [(0, 0), (1, 0), (2, 0), (3, 0),
                          (0, 1),                 (3, 1),
                          (0, 2),                 (3, 2),
                          (0, 3), (1, 3), (2, 3), (3, 3),
                          ],
                'shape': (4, 4)
            }
        }
    }
    sock.send_json(set_initial)
    player_handle_request(client_sock, team)

    assert sock.recv_json() == {
        '__uuid__': _uuid,
        '__return__': 'test stopping player'
    }

    _uuid = uuid.uuid4().__str__()
    get_move = {
        '__uuid__': _uuid,
        '__action__': "get_move",
        '__data__': {
            'game_state': {
                'team': {
                    'team_index': 0,
                    'bot_positions': [(1, 1), (1, 1)],
                    'score': 0,
                    'kills': [0]*2,
                    'deaths': [0]*2,
                    'bot_was_killed': [False]*2,
                    'error_count': 0,
                    'food': [(1, 1)],
                    'shaded_food': [(1, 1)],
                    'name': 'dummy',
                    'team_time': 0,
                },
                'enemy': {
                    'team_index': 1,
                    'bot_positions': [(2, 2), (2, 2)],
                    'score': 0,
                    'kills': [0]*2,
                    'deaths': [0]*2,
                    'bot_was_killed': [False]*2,
                    'food': [(2, 2)],
                    'shaded_food': [],
                    'name': 'other dummy',
                    'team_time': 0,
                    'is_noisy': [False, False],
                    'error_count': 0
                },
                'round': 1,
                'bot_turn': 0,
            }
        }
    }
    sock.send_json(get_move)
    player_handle_request(client_sock, team)

    assert sock.recv_json() == {
        '__uuid__': _uuid,
        '__return__': {
            "move": [1, 1],
            "say": None
        }
    }

    exit_msg = {
        '__uuid__': uuid.uuid4().__str__(),
        '__action__': "exit",
        '__data__': {}
    }
    sock.send_json(exit_msg)

    assert res[0] == True
