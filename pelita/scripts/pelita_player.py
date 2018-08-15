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

import zmq

import pelita
from ..player.team import new_style_team

_logger = logging.getLogger("pelita.scripts.pelita_player")

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


def make_client(team_spec, address):
    address = address.replace('*', 'localhost')

    try:
        team = load_team(team_spec)
    except Exception as e:
        context = zmq.Context()
        socket = context.socket(zmq.PAIR)
        try:
            socket.connect(address)
            query = socket.recv_json() # throw away the get_initial message
            socket.send_json({'__error__': 'Could not load %s' % team_spec})
        except zmq.ZMQError as e:
            raise IOError('failed to connect the client to address %s: %s'
                          % (address, e))

        raise

    print("Using team '%s' -> '%s'" % (team_spec, team.team_name))

    client = pelita.simplesetup.SimpleClient(team, address=address)
    return client

def create_builtin_team(spec):
    """
    Tries to build a builtin team from the given `spec`.
    """
    names = spec.split(',')
    if len(names) == 1:
        names *= 2
    elif len(names) > 2:
        raise MalformedBuiltinTeam('need two comma separated names')

    try:
        players = [import_builtin_player(name)() for name in names]
    except ValueError:
        raise
    teamname = 'The %ss' % players[0].__class__.__name__
    return pelita.player.SimpleTeam(teamname, *players)


def check_team_name(name):
    # Team name must be ascii
    try:
        name.encode('ascii')
    except UnicodeDecodeError:
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
    # if there is no : or / in the spec, we assume a built-in was given
    can_be_builtin = not os.sep in spec and not ':' in spec

    if can_be_builtin:
        try:
            team = create_builtin_team(spec)
            check_team_name(team.team_name)
            return team
        except MalformedBuiltinTeam:
            raise
        except ValueError:
            # We use some heuristic to find out if the user wanted to specify a
            # built-in player
            if ',' in spec:
                raise

    try:
        factory = load_factory(spec)
    except (FileNotFoundError, ImportError) as e:
        if can_be_builtin:
            pathname, _, factory_name = spec.partition(':')
            sane_players = {p.__name__: p for p in pelita.player.SANE_PLAYERS}
            others = ', '.join(list(sane_players.keys()))
            msg = 'Failed to find %s in players. (Available built-in players are: %s).' % (spec, others)
            raise ImportError(msg) from None
        else:
            print("failure while loading team '%s'" % spec, file=sys.stderr)
            print('ERROR: %s' % e, file=sys.stderr)
            raise
    except (ValueError, AttributeError, TypeError, IOError) as e:
        print("failure while loading team '%s'" % spec, file=sys.stderr)
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


def import_builtin_player(name):
    """
    Checks if `name` is in `pelita.player`. Raises ValueError, if it is not found.
    """
    if name == 'random':
        sane_players = {p.__name__: p for p in pelita.player.SANE_PLAYERS}
        name, player = random.choice(list(sane_players.items()))
        print('Choosing %s for random player' % name)
        return player
    else:
        try:
            return getattr(pelita.player, name)
        except AttributeError:
            # It is not a builtin player
            raise ValueError("{} is not a known built-in player.".format(name))

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
        client = make_client(args.team, args.address)
        ret = client.run()

    sys.exit(ret)

if __name__ == '__main__':
    main()
