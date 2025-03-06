
import concurrent.futures
import queue
import sys
import uuid

import pytest
import zmq

from pelita.game import play_turn, setup_game
from pelita.network import bind_socket
from pelita.scripts.pelita_player import player_handle_request
from pelita.team import make_team

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
        res.append("success")
        print(res)
        return bot.position

    sock = zmq_context.socket(zmq.PAIR)
    port = sock.bind_to_random_port('tcp://127.0.0.1')

    team, _ = make_team(stopping, team_name='test stopping player')
    client_sock = zmq_context.socket(zmq.PAIR)
    client_sock.connect(f'tcp://127.0.0.1:{port}')
    poller = zmq.Poller()
    poller.register(client_sock, zmq.POLLIN)

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
    player_handle_request(client_sock, poller, team)

    assert sock.recv_json() == {
        '__uuid__': _uuid,
        '__return__': None
    }

    _uuid = uuid.uuid4().__str__()
    get_move = {
        '__uuid__': _uuid,
        '__action__': "get_move",
        '__data__': {
            'game_state': {
                'team_index': 0,
                'bots': [(1, 1), (2, 2), (1, 1), (2, 2)],
                'score': [0, 0],
                'kills': [0]*4,
                'deaths': [0]*4,
                'bot_was_killed': [False]*4,
                'error_count': [0, 0],
                'food': [[(1, 1)], [(2, 2)]],
                'shaded_food': [[(1, 1)], []],
                'team_names': ['dummy', 'other_dummy'],
                'team_time': [0, 0],
                'is_noisy': [False, False, False, False],
                'error_count': [0, 0],
                'round': 1,
                'turn': 0,
                'timeout_length': 3,
                'max_rounds': 300,
            }
        }
    }
    sock.send_json(get_move)
    player_handle_request(client_sock, poller, team)

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

    assert res[0] == "success"


@pytest.mark.parametrize("checkpoint", range(11))
def test_simpleclient_broken(zmq_context, checkpoint):
    # This test runs a test game against a (malicious) server client
    # (a malicious subprocess client is harder to test)
    # Depending on the checkpoint selected, the broken test client will
    # run up to a particular point and then send a malicious message.

    # Depending on whether this message occurs in the game setup stage
    # or during the game run, this will either set the phase to FAILURE or
    # let the good team win. Pelita itself should not break in the process.

    timeout = 3000

    q1 = queue.Queue()
    q2 = queue.Queue()

    def dealer_good(q):
        zmq_context = zmq.Context()
        sock = zmq_context.socket(zmq.DEALER)
        poll = zmq.Poller()

        port = sock.bind_to_random_port('tcp://127.0.0.1')
        q.put(port)

        poll.register(sock, zmq.POLLIN)
        _available_socks = poll.poll(timeout=timeout)
        request = sock.recv_json()
        assert request['REQUEST']
        sock.send_json({'__status__': 'ok', '__data__': {'team_name': 'good player'}})

        _available_socks = poll.poll(timeout=timeout)
        set_initial = sock.recv_json(flags=zmq.NOBLOCK)
        if set_initial['__action__'] == 'exit':
            return
        assert set_initial['__action__'] == "set_initial"
        sock.send_json({'__uuid__': set_initial['__uuid__'], '__return__': None})

        for _i in range(8):
            _available_socks = poll.poll(timeout=timeout)
            game_state = sock.recv_json(flags=zmq.NOBLOCK)

            action = game_state['__action__']
            if action == 'exit':
                return
            assert set_initial['__action__'] == "set_initial"

            current_pos = game_state['__data__']['game_state']['team']['bot_positions'][game_state['__data__']['game_state']['bot_turn']]
            sock.send_json({'__uuid__': game_state['__uuid__'], '__return__': {'move': current_pos}})

        _available_socks = poll.poll(timeout=timeout)
        exit_state = sock.recv_json(flags=zmq.NOBLOCK)

        assert exit_state['__action__'] == 'exit'

    def dealer_bad(q):
        zmq_context = zmq.Context()
        sock = zmq_context.socket(zmq.DEALER)
        poll = zmq.Poller()

        port = sock.bind_to_random_port('tcp://127.0.0.1')
        q.put(port)

        poll.register(sock, zmq.POLLIN)
        # we set our recv to raise, if there is no message (zmq.NOBLOCK),
        # so we do not need to care to check whether something is in the _available_socks
        _available_socks = poll.poll(timeout=timeout)

        request = sock.recv_json(flags=zmq.NOBLOCK)
        assert request['REQUEST']
        if checkpoint == 1:
            sock.send_string("")
            return
        elif checkpoint == 2:
            sock.send_json({'__status__': 'ok'})
            return
        else:
            sock.send_json({'__status__': 'ok', '__data__': {'team_name': f'bad <{checkpoint}>'}})

        _available_socks = poll.poll(timeout=timeout)

        set_initial = sock.recv_json(flags=zmq.NOBLOCK)

        if checkpoint == 3:
            sock.send_string("")
            return
        elif checkpoint == 4:
            sock.send_json({'__uuid__': 'ok'})
            return
        else:
            sock.send_json({'__uuid__': set_initial['__uuid__'], '__data__': None})

        for _i in range(8):
            _available_socks = poll.poll(timeout=timeout)
            game_state = sock.recv_json(flags=zmq.NOBLOCK)

            action = game_state['__action__']
            if action == 'exit':
                return

            current_pos = game_state['__data__']['game_state']['team']['bot_positions'][game_state['__data__']['game_state']['bot_turn']]
            if checkpoint == 5:
                sock.send_string("No json")
                return
            elif checkpoint == 6:
                # This is an acceptable message that will never match a request
                # We can send the correct message afterwards and the match continues
                sock.send_json({'__uuid__': "Bad", '__return__': "Nothing"})
                sock.send_json({'__uuid__': game_state['__uuid__'], '__return__': {'move': current_pos}})
            elif checkpoint == 7:
                sock.send_json({'__uuid__': game_state['__uuid__'], '__return__': {'move': [0, 0]}})
                return
            elif checkpoint == 8:
                sock.send_json({'__uuid__': game_state['__uuid__'], '__return__': {'move': "NOTHING"}})
                return
            elif checkpoint == 9:
                sock.send_json({'__uuid__': game_state['__uuid__'], '__return__': {'move': [0, 0]}})
                return
            else:
                sock.send_json({'__uuid__': game_state['__uuid__'], '__return__': {'move': current_pos}})

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        players = []
        players.append(executor.submit(dealer_good, q1))

        if checkpoint == 0:
            players.append(executor.submit(dealer_good, q2))
        else:
            players.append(executor.submit(dealer_bad, q2))

        port1 = q1.get()
        port2 = q2.get()

        layout = {'walls': ((0, 0), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (1, 0), (1, 5), (2, 0), (2, 5), (3, 0), (3, 2), (3, 3), (3, 5), (4, 0), (4, 2), (4, 3), (4, 5), (5, 0), (5, 5), (6, 0), (6, 5), (7, 0), (7, 1), (7, 2), (7, 3), (7, 4), (7, 5)), 'food': [(1, 1), (1, 2), (2, 1), (2, 2), (5, 3), (5, 4), (6, 3), (6, 4)], 'bots': [(1, 3), (6, 2), (1, 4), (6, 1)], 'shape': (8, 6)}

        game_state = setup_game([
                f'pelita://127.0.0.1:{port1}/PLAYER1',
                f'pelita://127.0.0.1:{port2}/PLAYER2'
            ],
            layout_dict=layout,
            max_rounds=2,
            timeout_length=1,
            )

        # check that the game_state ends in the expected phase
        match checkpoint:
            case 0|5|6|7|8|9|10:
                assert game_state['game_phase'] == 'RUNNING'
            case 1|2|3|4:
                assert game_state['game_phase'] == 'FAILURE'

        while game_state['game_phase'] == 'RUNNING':
            game_state = play_turn(game_state)

        match checkpoint:
            case 0|6|10:
                assert game_state['game_phase'] == 'FINISHED'
                assert game_state['whowins'] == 2
            case 5|7|8|9:
                assert game_state['game_phase'] == 'FINISHED'
                assert game_state['whowins'] == 0
            case 1|2|3|4:
                assert game_state['game_phase'] == 'FAILURE'

        # check that no player had an uncaught exception
        for player in concurrent.futures.as_completed(players):
            assert player.exception() is None
