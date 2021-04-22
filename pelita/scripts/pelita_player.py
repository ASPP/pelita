#!/usr/bin/env python3

import argparse
import contextlib
import importlib
import logging
import os
from pathlib import Path
import signal
import subprocess
import sys

import json
import zmq

import pelita
from ..player.team import make_team
from ..network import json_default_handler
from .script_utils import start_logging

_logger = logging.getLogger(__name__)


DEFAULT_FACTORY = 'team'

@contextlib.contextmanager
def with_sys_path(dirname):
    sys.path.insert(0, dirname)
    try:
        yield
    finally:
        sys.path.remove(dirname)


def run_player(team_spec, address, color=None):
    """ Creates a team from `team_spec` and runs
    a game through the zmq PAIR socket on `address`.

    Parameters
    ----------
    team_spec : str
        path to the module that declares the team
    address : address to zmq PAIR socket
        the address of the remote team socket
    color : string, optional
        the color of the team (for nicer output)

    """

    address = address.replace('*', 'localhost')
    # Connect to the given address
    context = zmq.Context()
    socket = context.socket(zmq.PAIR)
    try:
        socket.connect(address)
    except zmq.ZMQError as e:
        raise IOError(f"Failed to connect the client to address {address}: {e}")

    try:
        team = load_team(team_spec)
    except Exception as e:
        # We could not load the team.
        # Wait for the set_initial message from the server
        # and reply with an error.
        try:
            json_message = socket.recv_unicode()
            py_obj = json.loads(json_message)
            uuid_ = py_obj["__uuid__"]
            action = py_obj["__action__"]
            data = py_obj["__data__"]

            socket.send_json({
                '__uuid__': uuid_,
                '__error__': e.__class__.__name__,
                '__error_msg__': f'Could not load {team_spec}: {e}'
            })
        except zmq.ZMQError as e:
            raise IOError('failed to connect the client to address %s: %s'
                          % (address, e))
        # TODO: Do not raise here but wait for zmq to return a sensible error message
        # We need a way to distinguish between syntax errors in the client
        # and general zmq disconnects
        raise

    if color == 'blue':
        pie = '\033[94m' + 'ᗧ' + '\033[0m'
    elif color == 'red':
        pie = '\033[91m' + 'ᗧ' + '\033[0m'
    else:
        pie = 'ᗧ'
    if pelita.game._mswindows:
        print(f"{color} team '{team_spec}' -> '{team.team_name}'")
    else:
        print(f"{pie} {color} team '{team_spec}' -> '{team.team_name}'")

    while True:
        cont = player_handle_request(socket, team)
        if not cont:
            return


def player_handle_request(socket, team):
    """ Awaits a new request on `socket` and dispatches it
    to `team`.

    Parameters
    ----------
    socket : zmq PAIR socket
        the connection to the main pelita game
    team : a Team object
        the team that handles the requests

    Returns
    -------
    continue_processing : bool
        True if still running, False on exit

    """

    # Waits for incoming requests and tries to get a proper
    # answer from the player.

    try:
        json_message = socket.recv_unicode()
        py_obj = json.loads(json_message)
        msg_id = py_obj["__uuid__"]
        action = py_obj["__action__"]
        data = py_obj["__data__"]
        _logger.debug("<o-- %r [%s]", action, msg_id)

        # feed client actor here …
        if action == "set_initial":
            retval = team.set_initial(**data)
        elif action == "get_move":
            retval = team.get_move(**data)
        elif action == "team_name":
            retval = team.team_name
        elif action == "exit":
            # quit and don’t return anything
            message_obj = {
                "__uuid__": msg_id,
                "__return__": None
            }
            return False
        else:
            _logger.warning(f"Player received unknown action {action}.")

        message_obj = {
            "__uuid__": msg_id,
            "__return__": retval
        }

        # retval can be a string with a team name,
        # a dict with a move and optionally additional data,
        # or a dict with error key and message, if something
        # went wrong

        if isinstance(retval, dict) and 'error' in retval:
            # The team class has flagged an error.
            # We return the result (in the finally clause)
            # but return false to exit the process.
            return False
        else:
            # continue
            return True

    except KeyboardInterrupt as e:
        # catch KeyboardInterrupt to avoid spamming stderr
        msg_id = None
        message_obj = {
            '__error__': e.__class__.__name__
        }
        return True

    except Exception as e:
        # All client exceptions should have been caught in the
        # team class. This clause is a safety net for
        # exceptions that are not caused by a bot.

        msg = "Exception in client code for team %s." % team
        print(msg, file=sys.stderr)
        message_obj = {
            '__uuid__': msg_id,
            '__error__': e.__class__.__name__,
            '__error_msg__': str(e)
        }
        return False

    finally:
        # we use our own json_default_handler
        # to automatically convert numpy ints to json
        json_message = json.dumps(message_obj, default=json_default_handler)
        # return the message
        socket.send_unicode(json_message)
        if '__error__' in message_obj:
            _logger.warning("o-!> %r [%s]", message_obj['__error__'], msg_id)
        else:
            _logger.debug("o--> %r [%s]", message_obj['__return__'], msg_id)


def check_team_name(name):
    # Team name must be ascii
    try:
        name.encode('ascii')
    except UnicodeEncodeError:
        raise ValueError('Invalid team name (non ascii): "%s".'%name)
    # Team name must be shorter than 25 characters
    if len(name) > 25:
        raise ValueError('Invalid team name (longer than 25): "%s".'%name)
    if len(name) == 0:
        raise ValueError('Invalid team name (too short).')
    # Check every character and make sure it is either
    # a letter or a number. Nothing else is allowed.
    for char in name:
        if (not char.isalnum()) and (char != ' '):
            raise ValueError('Invalid team name (only alphanumeric '
                             'chars or blanks): "%s"'%name)
    if name.isspace():
        raise ValueError('Invalid team name (no letters): "%s"'%name)


def load_team(spec):
    """ Tries to load a team from a given spec.

    At first it will check if it can build a team from the built-in players.
    If this fails, it will try to load a factory.
    """
    if spec == '0':
        from ..player import SmartEatingPlayer
        return team_from_module(SmartEatingPlayer)
    elif spec == '1':
        from ..player import SmartRandomPlayer
        return team_from_module(SmartRandomPlayer)
    try:
        team = load_team_from_module(spec)
    except (FileNotFoundError, ImportError, ValueError,
            AttributeError, TypeError, IOError) as e:
        print("Failure while loading team '%s'" % spec, file=sys.stderr)
        print('ERROR: %s' % e, file=sys.stderr)
        raise

    check_team_name(team.team_name)
    return team

def load_team_from_module(path: str):
    """ Tries to load and return a team from a given path.

    The path should be a Python module (which can be a folder with an
    __init__.py file) or an importable .py file.
    The module must contain a function `move` and a variable `TEAM_NAME`.

    Parameters
    ----------
    pathspec : str
        the location of the importable module

    Returns
    -------
    factory : function
        the factory method that should produce a team

    Raises
    ------
    ValueError
        if a module is already present in sys.modules
    AttributeError
        if the module has no factory with the given name
    ModuleNotFoundError
        if the module cannot be found
    FileNotFoundError
        if the parent folder cannot be found
    """
    path = Path(path)

    if not path.parent.exists():
        raise FileNotFoundError("Folder {} does not exist.".format(path.parent))

    dirname = str(path.parent)
    modname = path.stem

    if modname in sys.modules:
        raise ValueError("A module named ‘{}’ has already been imported.".format(modname))

    with with_sys_path(dirname):
        module = importlib.import_module(modname)

    return team_from_module(module)


def team_from_module(module):
    """ Looks for a move function and a team name in
    `module` and returns a team.
    """
    # look for a new-style team
    move = getattr(module, "move")
    name = getattr(module, "TEAM_NAME")
    if not callable(move):
        raise TypeError("move is not a function")
    if type(name) is not str:
        raise TypeError("TEAM_NAME is not a string")
    team, _ = make_team(move, team_name=name)
    return team


def with_zmq_router(team, address):
    dealer_pair_mapping = {}
    pair_dealer_mapping = {}
    proc_dealer_mapping = {}

    def cleanup(signum, frame):
        for proc in proc_dealer_mapping:
            proc.terminate()
        sys.exit()

    signal.signal(signal.SIGTERM, cleanup)

    ctx = zmq.Context()
    sock = ctx.socket(zmq.ROUTER)
    sock.bind(address)

    poll = zmq.Poller()
    poll.register(sock, zmq.POLLIN)

    while True:
        evts = dict(poll.poll(1000))
        if sock in evts:
            id_ = sock.recv()
            msg = sock.recv_json()
            if "REQUEST" in msg:
                pair_sock = ctx.socket(zmq.PAIR)
                port = pair_sock.bind_to_random_port('tcp://127.0.0.1')
                pair_addr = 'tcp://127.0.0.1:{}'.format(port)

                poll.register(pair_sock, zmq.POLLIN)

                _logger.info("Starting match for team {}. ({} already running.)".format(team, len(proc_dealer_mapping)))
                sub = play_remote(team, pair_addr)

                dealer_pair_mapping[id_] = pair_sock
                pair_dealer_mapping[pair_sock] = id_
                proc_dealer_mapping[sub] = (id_, pair_sock)

                assert len(dealer_pair_mapping) == len(pair_dealer_mapping)
            elif id_ in dealer_pair_mapping:
                dealer_pair_mapping[id_].send_json(msg)
            else:
                _logger.info("Unknown incoming DEALER and not a request.")

        elif len(evts):
            for pair_sock, id_ in pair_dealer_mapping.items():
                if pair_sock in evts:
                    msg = pair_sock.recv()
                    sock.send_multipart([id_, msg])

        old_procs = list(proc_dealer_mapping.keys())
        count = 0
        for proc in old_procs:
            if proc.poll() is not None:
                id_, pair_sock = proc_dealer_mapping[proc]
                del dealer_pair_mapping[id_]
                del pair_dealer_mapping[pair_sock]
                del proc_dealer_mapping[proc]
                count += 1
        if count:
            _logger.debug("Cleaned up {} process(es). ({} still running.)".format(count, len(proc_dealer_mapping)))


def play_remote(team, pair_addr):
    player_path = os.environ.get("PELITA_PATH") or os.path.dirname(sys.argv[0])
    player = 'pelita.scripts.pelita_player'
    external_call = [sys.executable,
                    '-m',
                    player,
                    team,
                    pair_addr]
    _logger.debug("Executing: %r", external_call)
    sub = subprocess.Popen(external_call)
    return sub


def main():
    parser = argparse.ArgumentParser(description="Runs a Python pelita module.")
    parser.add_argument('--log', help='print debugging log information to LOGFILE (default \'stderr\')',
                        metavar='LOGFILE', default=argparse.SUPPRESS, nargs='?')
    parser.add_argument('--remote', help='bind to a zmq.ROUTER socket at the given address which forks subprocesses on demand',
                        action='store_const', const=True)
    parser.add_argument('--color', help='which color your team will have in the game', default=None)
    parser.add_argument('team')
    parser.add_argument('address')

    args = parser.parse_args()

    try:
        start_logging(args.log)
    except AttributeError:
        pass

    if args.remote:
        with_zmq_router(args.team, args.address)
    else:
        run_player(args.team, args.address, args.color)


if __name__ == '__main__':
    main()
