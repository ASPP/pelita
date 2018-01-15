#!/usr/bin/env python3

import argparse
import inspect
import keyword
import logging
import os
import random
import signal
import string
import subprocess
import sys

import pelita

_logger = logging.getLogger("pelita.scripts.pelita_player")

DEFAULT_FACTORY = 'team'

def make_client(team_spec, address):
    team = load_team(team_spec)
    print("Using team '%s' -> '%s'" % (team_spec, team.team_name))

    addr = address
    addr = addr.replace('*', 'localhost')
    client = pelita.simplesetup.SimpleClient(team, address=addr)
    return client

def check_module(filepath):
    "Throws an ValueError is the specified path is neither a module nor a package."
    if not os.path.exists(filepath):
        raise ValueError("'%s' doesn't exist" % filepath)
    allowed = string.ascii_letters + string.digits + '_'
    if filepath.endswith('.py'):
        valid = os.path.isfile(filepath)
        modname = os.path.basename(filepath[:-3])
    else:
        initpy = os.path.join(filepath, '__init__.py')
        valid = os.path.isdir(filepath) and os.path.isfile(initpy)
        modname = os.path.basename(filepath.rstrip(os.path.sep))
    if (set(modname) - set(allowed) or
        modname[0] in string.digits or
        modname in keyword.kwlist or
        modname.startswith('__')):
        raise ValueError("invalid module name: '%s'" % modname)

    if not valid:
        raise ValueError("'%s': neither a module nor a package" % filepath )

def create_builtin_team(spec):
    names = spec.split(',')
    if len(names) == 1:
        names *= 2
    elif len(names) > 2:
        raise ValueError('need two comma separated names')

    players = [import_builtin_player(name)() for name in names]
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
    try:
        if '/' in spec or spec.endswith('.py') or os.path.exists(spec):
            team = load_factory(spec)()
        else:
            team = create_builtin_team(spec)
        check_team_name(team.team_name)
        return team
    except (ValueError, AttributeError, IOError, ImportError) as e:
        print("failure while loading team '%s'" % spec, file=sys.stderr)
        print('ERROR: %s' % e, file=sys.stderr)
        raise

def load_factory(filespec):
    filename, _, factory_name = filespec.partition(':')
    check_module(filename)
    filename = filename.rstrip(os.path.sep)
    dirname = os.path.dirname(filename)
    modname = os.path.splitext(os.path.basename(filename))[0]

    factory_name = factory_name or DEFAULT_FACTORY
    with pelita.utils.with_sys_path(dirname):
        module = __import__(modname, fromlist=[factory_name])
    return getattr(module, factory_name)

def import_builtin_player(name):
    with pelita.utils.with_sys_path("./"):
        players_module = __import__('pelita.player', fromlist='players')
        sane_players = {p.__name__: p for p in players_module.SANE_PLAYERS}

    if name == 'random':
        player = random.choice(list(sane_players.values()))
        print('Choosing %s for random player' % player)
    else:
        player = sane_players.get(name)
        if not player:
            try:
                # fallback to player in pelita.player
                player = getattr(pelita.player, name)
            except AttributeError:
                others = ', '.join(list(sane_players.keys()))
                msg = 'Failed to find %s in players. (Available players are: %s).' % (name, others)
                raise ImportError(msg)

    if inspect.isclass(player) and issubclass(player, pelita.player.AbstractPlayer):
        return player
    else:
        raise ImportError("%r is not a valid player." % player)

def with_zmq_router(team, address):
    dealer_pair_mapping = {}
    pair_dealer_mapping = {}
    proc_dealer_mapping = {}

    def cleanup(signum, frame):
        for proc in proc_dealer_mapping:
            proc.terminate()
        sys.exit()

    signal.signal(signal.SIGTERM, cleanup)

    import zmq
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
        pelita.utils.start_logging(args.log)
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
