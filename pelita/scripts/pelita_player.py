#!/usr/bin/env python3

import argparse
import contextlib
import importlib
import inspect
import keyword
import logging
import os
from pathlib import Path
import random
import signal
import string
import subprocess
import sys

import json
import zmq

import pelita
from ..player.team import new_style_team, make_team

_logger = logging.getLogger(__name__)

class MalformedBuiltinTeam(ValueError):
    pass

DEFAULT_FACTORY = 'team'

@contextlib.contextmanager
def with_sys_path(dirname):
    sys.path.insert(0, dirname)
    try:
        yield
    finally:
        sys.path.remove(dirname)


def make_client(team_spec, address, color=None):
    address = address.replace('*', 'localhost')

    try:
        team = load_team(team_spec)
    except Exception as e:
        # We could not load the team.
        # Wait for the set_initial message from the server
        # and reply with an error.
        context = zmq.Context()
        socket = context.socket(zmq.PAIR)
        try:
            socket.connect(address)
            json_message = socket.recv_unicode()
            py_obj = json.loads(json_message)
            uuid_ = py_obj["__uuid__"]
            action = py_obj["__action__"]
            data = py_obj["__data__"]

            socket.send_json({'__uuid__': uuid_, '__error__': 'Could not load %s' % team_spec})
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
    print(f"{pie} {color} team '{team_spec}' -> '{team.team_name}'")

    client = pelita.simplesetup.SimpleClient(team, address=address)
    return client


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

# helper teams for the demo mode
# TODO: Rewrite the old demo players to the new API
def stopping(bot, state):
    return bot.position, state

def random(bot, state):
    import random
    return random.choice(bot.legal_positions), state

def load_team(spec):
    """ Tries to load a team from a given spec.

    At first it will check if it can build a team from the built-in players.
    If this fails, it will try to load a factory.
    """
    if spec == '0':
        #from ..player.FoodEatingPlayer import team
        #return team()
        team, _ = make_team(stopping, team_name="stopping")
        return team
    elif spec == '1':
        #from ..player.RandomExplorerPlayer import team
        team, _ = make_team(random, team_name="random")
        return team
    try:
        factory = load_factory(spec)
    except (FileNotFoundError, ImportError, ValueError,
            AttributeError, TypeError, IOError) as e:
        print("Failure while loading team '%s'" % spec, file=sys.stderr)
        print('ERROR: %s' % e, file=sys.stderr)
        raise
    try:
        team = factory()
    except TypeError:
        print("Factory for {} is not callable.".format(spec), file=sys.stderr)
        raise

    check_team_name(team.team_name)
    return team

def load_factory(pathspec: str):
    """ Tries to load and return a factory from a given pathspec.

    The pathspec is a path to a module (which can be a folder with an
    __init__.py file) or an importable .py file, followed by an optional ":"
    and the name of a factory method (defaults to "team") that returns a
    SimpleTeam.

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
    # strip off the factory_name after the first :
    pathname, _, factory_name = pathspec.partition(':')
    factory_name = factory_name or DEFAULT_FACTORY

    path = Path(pathname)

    if not path.parent.exists():
        raise FileNotFoundError("Folder {} does not exist.".format(path.parent))

    dirname = str(path.parent)
    modname = path.stem

    if modname in sys.modules:
        raise ValueError("Module {} has already been imported.".format(modname))

    with with_sys_path(dirname):
        module = importlib.import_module(modname)

    try:
        return getattr(module, factory_name)
    except AttributeError as e:
        return new_style_team(module)


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
    external_call = [pelita.libpelita.get_python_process(),
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
        pelita.libpelita.start_logging(args.log)
    except AttributeError:
        pass

    if args.remote:
        with_zmq_router(args.team, args.address)
    else:
        client = make_client(args.team, args.address, args.color)
        ret = client.run()

    sys.exit(ret)

if __name__ == '__main__':
    main()
