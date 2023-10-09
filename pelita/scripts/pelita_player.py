#!/usr/bin/env python3

import contextlib
from dataclasses import dataclass
import importlib
import json
import logging
from pathlib import Path
import random
import signal
import subprocess
import sys
from urllib.parse import urlparse

import click
from rich import print as pprint
from rich.progress import Progress
import zeroconf
import zmq

import pelita
from ..team import make_team
from ..network import json_default_handler, PELITA_PORT
from .script_utils import start_logging

_logger = logging.getLogger(__name__)


MAX_CONNECTIONS = 100


zeroconf.log.setLevel(logging.INFO)
zeroconf.log.addHandler(_logger)

@contextlib.contextmanager
def with_sys_path(dirname):
    sys.path.insert(0, dirname)
    try:
        yield
    finally:
        sys.path.remove(dirname)


@dataclass
class GameInfo:
    round: int|None
    max_rounds: int
    my_index: int
    my_name: str
    my_score: int
    enemy_name: str
    enemy_score: int
    finished: bool = False

    def status(self):
        plural = "s" if (self.round is not None and self.round > 1) else ""
        finished = f"[b]Finished[/b] ({self.round} round{plural}): " if self.finished else ""
        if self.my_index == 0:
            return f"{finished}[u]{self.my_name} ({self.my_score})[/u] vs {self.enemy_name} ({self.enemy_score})"
        else:
            return f"{finished}{self.enemy_name} ({self.enemy_score}) vs [u]{self.my_name} ({self.my_score})[/u]"


def run_player(team_spec, address, color=None, silent=False):
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

    if not silent:
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
    move = module.move
    name = module.TEAM_NAME
    if not callable(move):
        raise TypeError("move is not a function")
    if not isinstance(name, str):
        raise TypeError("TEAM_NAME is not a string")
    team, _ = make_team(move, team_name=name)
    return team


def zeroconf_advertise(address, port, team_specs):
    parsed_url = urlparse("tcp://" + address + ":" + str(port))
    if parsed_url.scheme != "tcp":
        _logger.warning("Can only advertise to tcp addresses.")
        return
    if parsed_url.hostname == "0.0.0.0":
        _logger.warning("Can only advertise to a specific interface.")
        return

    zc = zeroconf.Zeroconf()

    for team, path in team_specs:
        name = _check_team(team)

        desc = {
            'spec': team,
            'team_name': name,
            'proto_version': 0.2,
            'path': path,
        }
        full_name = f"{name}._pelita-player._tcp.local."
        info = zeroconf.ServiceInfo(
            "_pelita-player._tcp.local.",
            full_name,
            parsed_addresses=[parsed_url.hostname],
            #server='mynewserver.local',
            port=parsed_url.port,
            properties=desc,
        )

        print(f"Registration of service {full_name}, press Ctrl-C to exit...")
        zc.register_service(info)


def with_zmq_router(team_specs, address, port, *, advertise: str, session_key: str, show_progress: bool = True):
    # TODO: Explain how ROUTER-DEALER works with ZMQ

    # maps zmq dealer id to pair socket
    dealer_pair_mapping = {}
    # maps zmq dealer to progress bar
    dealer_progress_mapping = {}
    # maps pair socket to zmq dealer id
    pair_dealer_mapping = {}
    # maps subprocess to (dealer id, pair socket)
    proc_dealer_mapping = {}

    def cleanup(signum, frame):
        for proc in proc_dealer_mapping:
            proc.terminate()
        sys.exit()

    signal.signal(signal.SIGTERM, cleanup)

    ctx = zmq.Context()
    router_sock = ctx.socket(zmq.ROUTER)
    router_sock.bind(f"tcp://{address}:{port}")

    if advertise:
        zeroconf_advertise(advertise, port, team_specs)

    poll = zmq.Poller()
    poll.register(router_sock, zmq.POLLIN)

    from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn

    # TODO handle show_progress

    with Progress(
        SpinnerColumn(),
        *Progress.get_default_columns(),
        TimeElapsedColumn(),
    ) as progress:


        while True:
            incoming_evts = dict(poll.poll(1000))
            if router_sock in incoming_evts:
                dealer_id = router_sock.recv()
                # TODO: This should recover from failure
                msg = router_sock.recv_json()
                if "QUERY-SERVER" in msg:
                    pass

                elif "ADD-HOST" in msg:
                    # check key
                    if not msg.get('key', None) == session_key:
                        continue

                elif "RELOAD" in msg:
                    # check key
                    if not msg.get('key', None) == session_key:
                        continue

                elif "REQUEST" in msg:
                    if len(proc_dealer_mapping) >= MAX_CONNECTIONS:
                        _logger.warn("Exceeding maximum number of connections. Ignoring")
                        continue

                    requested_url = urlparse(msg['REQUEST'])
                    progress.console.print(f"Match requested: {requested_url.path}")

                    team_spec = team_specs[0][0]
                    for spec, path in team_specs:
                        if requested_url.path == '/' + path:
                            team_spec = spec
                            break
                    else:
                        # not found. use default but warn
                        progress.console.print(f"Player for path {requested_url.path} not found. Using default.")

                    info = GameInfo(round=None, max_rounds=None, my_index=0,
                                    my_name="waiting", my_score=0,
                                    enemy_name="waiting", enemy_score=0)
                    task = progress.add_task(info.status(), total=info.max_rounds)
                    dealer_progress_mapping[dealer_id] = (task, info)

                    # incoming message is a new request
                    pair_sock = ctx.socket(zmq.PAIR)
                    port = pair_sock.bind_to_random_port('tcp://127.0.0.1')
                    pair_addr = 'tcp://127.0.0.1:{}'.format(port)

                    poll.register(pair_sock, zmq.POLLIN)

                    num_running = len(proc_dealer_mapping)
                    _logger.info(f"Starting match for team {team_specs}. ({num_running} already running.)")
                    subproc = play_remote(team_spec, pair_addr, silent=show_progress)

                    dealer_pair_mapping[dealer_id] = pair_sock
                    pair_dealer_mapping[pair_sock] = dealer_id
                    proc_dealer_mapping[subproc] = (dealer_id, pair_sock)

                    assert len(dealer_pair_mapping) == len(pair_dealer_mapping)
                elif dealer_id in dealer_pair_mapping:
                    # incoming message refers to an existing connection

                    task, info = dealer_progress_mapping[dealer_id]

                    try:
                        is_exit = msg['__action__'] == 'exit'
                    except KeyError:
                        is_exit = False

                    if is_exit:
                        progress.stop_task(task)
                        progress.update(task, visible=False)
                        info.finished = True
                        progress.console.print(info.status())

                    try:
                        info.round = msg['__data__']['game_state']['round']
                        info.max_rounds = msg['__data__']['game_state']['max_rounds']
                    except KeyError:
                        info.round = None

                    if round is not None:
                        progress.update(task, completed=info.round, total=info.max_rounds)

                    try:
                        info.my_index = msg['__data__']['game_state']['team']['team_index']
                        info.my_name = msg['__data__']['game_state']['team']['name']
                        info.my_score = msg['__data__']['game_state']['team']['score']
                        info.enemy_name = msg['__data__']['game_state']['enemy']['name']
                        info.enemy_score = msg['__data__']['game_state']['enemy']['score']

                        progress.update(task, description=info.status())
                    except KeyError:
                        pass

                    dealer_pair_mapping[dealer_id].send_json(msg)
                else:
                    _logger.info("Unknown incoming DEALER and not a request.")

            elif len(incoming_evts):
                # One or more of our spawned players has replied
                for pair_sock, dealer_id in pair_dealer_mapping.items():
                    if pair_sock in incoming_evts:
                        msg = pair_sock.recv()
                        # route message back
                        router_sock.send_multipart([dealer_id, msg])

            old_procs = list(proc_dealer_mapping.keys())
            count = 0
            for proc in old_procs:
                if proc.poll() is not None:
                    dealer_id, pair_sock = proc_dealer_mapping[proc]
                    del dealer_pair_mapping[dealer_id]
                    del pair_dealer_mapping[pair_sock]
                    del proc_dealer_mapping[proc]
                    count += 1
            if count:
                _logger.debug("Cleaned up {} process(es). ({} still running.)".format(count, len(proc_dealer_mapping)))


def play_remote(team_spec, pair_addr, silent=False):
    external_call = [sys.executable,
                    '-m',
                    'pelita.scripts.pelita_player',
                    'remote-game',
                    team_spec,
                    pair_addr,
                    *(['--silent'] if silent else []),
                    ]
    _logger.debug("Executing: %r", external_call)
    sub = subprocess.Popen(external_call)
    return sub

def _check_team(team_spec):
    external_call = [sys.executable,
                    '-m',
                    'pelita.scripts.pelita_player',
                    'check-team',
                    team_spec]
    _logger.debug("Executing: %r", external_call)
    res = subprocess.run(external_call, capture_output=True, text=True)
    return res.stdout.strip()

@click.group()
@click.option('--log',
              is_flag=False, flag_value="-", default=None, metavar='LOGFILE',
              help="print debugging log information to LOGFILE (default 'stderr')")
def main(log):
    if log is not None:
        start_logging(log)


@main.command(help="bind a zmq.ROUTER socket at the given address which forks subprocesses on demand")
@click.option('--address', default="0.0.0.0")
@click.option('--port', default=PELITA_PORT)
@click.option('--team', '-t', 'teams', type=(str, str), multiple=True, required=True, help="Team path")
@click.option('--advertise', default=None, type=str,
              help='advertise player on zeroconf')
@click.option('--show-progress', is_flag=True, default=True)
def remote_server(address, port, teams, advertise, show_progress):
    for team, path in teams:
        team_name = _check_team(team)
        _logger.info(f"Mapping team {team} ({team_name}) to path {path}")

    session_key = "".join(str(random.randint(0, 9)) for _ in range(12))
    pprint(f"Use --session-key {session_key} to for the admin API.")
    with_zmq_router(teams, address, port, advertise=advertise, session_key=session_key, show_progress=show_progress)

    # asyncio repl …
    # reload via zqm key


@main.command()
@click.argument('team')
@click.argument('address')
@click.option('--color',
              default=None,
              help='which color your team will have in the game')
@click.option('--silent', is_flag=True, default=False)
def remote_game(team, address, color, silent):
    run_player(team, address, color, silent=silent)


@main.command("check-team")
@click.argument('team')
def cli_check_team(team):
    return check_team(team)

def check_team(team):
    print(load_team(team).team_name)


if __name__ == '__main__':
    main()
