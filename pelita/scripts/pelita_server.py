#!/usr/bin/env python3

from dataclasses import dataclass
import json
import logging

import queue
import shlex
import signal
import subprocess
import sys
import time
import urllib
import urllib.parse
from typing import Optional, Dict, List
from urllib.parse import urlparse
from random import Random
from weakref import WeakValueDictionary

import click
from rich import print as pprint
from rich.progress import Progress, SpinnerColumn, MofNCompleteColumn, BarColumn, TextColumn, TimeElapsedColumn, Task
import yaml
import zeroconf
import zmq

from ..network import PELITA_PORT
from .script_utils import start_logging

_logger = logging.getLogger(__name__)

zeroconf.log.setLevel(logging.INFO)
zeroconf.log.addHandler(_logger)

DEFAULT_MAX_CONNECTIONS = 50

# TODO: This timeout should be shorter
# once a connection has been established
SEND_QUEUE_TIMEOUT = 5. # seconds

@dataclass
class GameInfo:
    round: Optional[int]
    max_rounds: int
    my_index: int
    my_name: str
    my_score: int
    enemy_name: str
    enemy_score: int
    finished: bool = False
    last_msg: Optional[bytes] = None

    def status(self):
        plural = "" if self.round == 1 else "s"
        finished = f"[b]Finished[/b] ({self.round if self.round is not None else '-'} round{plural}): " if self.finished else ""
        my_name = self.my_name or "[dim]unknown[/dim]"
        enemy_name = self.enemy_name or "[dim]unknown[/dim]"
        if self.my_index == 0:
            return f"{finished}[u]{my_name}[/u] ({self.my_score}) vs {enemy_name} ({self.enemy_score})"
        else:
            return f"{finished}{enemy_name} ({self.enemy_score}) vs [u]{my_name}[/u] ({self.my_score})"

@dataclass(frozen=True)
class ProcessInfo:
    proc: subprocess.Popen
    task: Task
    info: GameInfo
    dealer_id: bytes
    pair_socket: zmq.Socket

@dataclass
class TeamInfo:
    spec: str
    team_name: str
    zeroconf_name: str = None
    server_path: str = None
    team_name_override: str = None
    silent_bots: bool = False


def zeroconf_register(zc, address, port, team_spec, path, print=print):
    parsed_url = urlparse("tcp://" + address + ":" + str(port))
    if parsed_url.scheme != "tcp":
        _logger.warning("Can only advertise to tcp addresses.")
        return
    if parsed_url.hostname == "0.0.0.0":
        _logger.warning("Can only advertise to a specific interface.")
        return

    name = _check_team(team_spec)

    desc = {
        'spec': team_spec,
        'team_name': name,
        'proto_version': 0.2,
        'path': '/' + path,
    }

    # there is a chance that our name is already taken.
    # We try for a few times with different names before we give up
    suffixes = ["", "-1", "-2", "-3", "-4"]

    for suffix in suffixes:
        full_name = f"{name}{suffix}._pelita-player._tcp.local."
        info = zeroconf.ServiceInfo(
            "_pelita-player._tcp.local.",
            full_name,
            parsed_addresses=[parsed_url.hostname],
            #server='mynewserver.local',
            port=parsed_url.port,
            properties=desc,
        )

        print(f"Registration of service {full_name}")
        try:
            zc.register_service(info)
            return info
        except zeroconf.NonUniqueNameException as e:
            print(f"Name {full_name} already taken. Trying alternative")
            continue

    print(f"No alternative found after {len(suffixes)} tries. Not advertising the player.")
    return None

def zeroconf_deregister(zc: zeroconf.Zeroconf, info: zeroconf.ServiceInfo):
    zc.unregister_service(info)

class PelitaServer:
    # TODO: Explain how ROUTER-DEALER works with ZMQ

    def __init__(self, team_infos: List[TeamInfo], address, port, *, advertise: str, session_key: str,
                 max_connections: int):

        self.team_infos = team_infos

        self.address = address
        self.port = port
        self.advertise = advertise
        self.session_key = session_key
        self.max_connections = max_connections

        # maps socket/process/game data
        self.connection_map: Dict[bytes, ProcessInfo] = {}
        self.connections_by_pair_socket = WeakValueDictionary() # automatic cache

        # maps team_spec, path to zc.ServiceInfo
        self.team_serviceinfo_mapping = {}

        def cleanup(_signum, _frame):
            for process_info in self.connection_map.values():
                _logger.warning(f"Terminating unfinished process: ‘{shlex.join(process_info.proc.args)}’.")
                process_info.proc.terminate()
            finish_time = time.monotonic() + 3
            for process_info in self.connection_map.values():
                # We need to wait for all processes to finish
                # Otherwise we might exit before the signal has been sent
                _logger.debug(f"Waiting for process ‘{shlex.join(process_info.proc.args)}’ to terminate.")
                remainder = finish_time - time.monotonic()
                if remainder > 0:
                    try:
                        process_info.proc.wait(remainder)
                    except subprocess.TimeoutExpired:
                        _logger.warning(f"Process ‘{shlex.join(process_info.proc.args)}’ has not finished.")

            sys.exit()

        signal.signal(signal.SIGTERM, cleanup)
        signal.signal(signal.SIGINT, cleanup)

        self.ctx = zmq.Context()
        self.router_sock = self.ctx.socket(zmq.ROUTER)
        self.router_sock.bind(f"tcp://{self.address}:{self.port}")

        self.poll = zmq.Poller()
        self.poll.register(self.router_sock, zmq.POLLIN)

        self.ticks_progressbar = 0.0
        self.ticks_process_cleanup = 0.0

        self.send_queue = queue.SimpleQueue()

    def handle_send_queue(self):
        if self.send_queue.qsize() == 0:
            # The check for the qsize is not reliable and we only
            # use it as an optimisation to skip early
            return

        # Handle all unsent messages to pair sockets
        unsent = set()
        try:
            while True:
                data = self.send_queue.get(block=False)
                time_monotonic, dealer_id, message = data
                if time.monotonic() - time_monotonic > SEND_QUEUE_TIMEOUT:
                    # discard
                    _logger.warning(f"Could not send to dealer id {dealer_id.hex()}.")
                    continue

                if dealer_id not in self.connection_map:
                    _logger.warning(f"Could not send to dealer id {dealer_id.hex()}.")
                    continue

                process_info = self.connection_map[dealer_id]
                process_info.info.last_msg = message

                # Problem: When the receiving end of the pair socket has crashed, then
                # a simple send will halt forever.
                if process_info.pair_socket.poll(0, flags=zmq.POLLOUT) == zmq.POLLOUT:
                    process_info.pair_socket.send(message)
                else:
                    unsent.add(data)

        except queue.Empty:
            for data in unsent:
                self.send_queue.put(data)

    def handle_known_client(self, dealer_id, message, progress):
        # We try to send to the pair socket immediately
        # If this fails, we enqueue the message and send it again later

        process_info = self.connection_map[dealer_id]
        process_info.info.last_msg = message

        try:
            process_info.pair_socket.send(message, flags=zmq.NOBLOCK)
        except zmq.ZMQError:
            data = time.monotonic(), dealer_id, message
            self.send_queue.put(data)
        return


    def handle_new_connection(self, dealer_id, message, progress):
        try:
            msg_obj = json.loads(message)
        except ValueError as e:
            _logger.debug(f"Error {e!r} when parsing incoming message. Ignoring.")
            return

        # TODO actions
        # stop server - do not accept new requests
        # purge server - drop all running connections

        if "STATUS" in msg_obj:
            # check key
            if not msg_obj.get('key', None) == self.session_key:
                return

            progress.console.print("List of teams:")
            for team in self.team_infos:
                progress.console.print(team)

        elif "TEAM" in msg_obj:
            # check key
            if not msg_obj.get('key', None) == self.session_key:
                return

            team_spec = msg_obj.get('team_spec')

            if msg_obj.get('TEAM') == 'ADD':
                team_info = load_team_info(team_spec)
                self.team_infos.append(team_info)
                info = zeroconf_register(self.zc, self.advertise, self.port, team.spec, team.server_path, print=progress.console.print)
                if info:
                    self.team_serviceinfo_mapping[(team.spec, team.server_path)] = info

            if msg_obj.get('TEAM') == 'REMOVE':
                # TODO: cannot remove from self.team_infos yet
                info = self.team_serviceinfo_mapping[(team.spec, team.server_path)]
                zeroconf_deregister(self.zc, info)

        elif "SCAN" in msg_obj:
            # return list of available bots
            if len(self.connection_map) >= self.max_connections:
                _logger.warning("Exceeding maximum number of connections. Ignoring")
                self.router_sock.send_multipart([dealer_id, b"NOCONN"])
                return

            requested_url = urlparse(msg_obj['SCAN'])
            progress.console.log(f"SCAN from id {dealer_id.hex()}: {requested_url.scheme}://{requested_url.hostname}{requested_url.path}")

            avaliable_teams = {}
            for team_info in self.team_infos:
                # we construct the url from the url that reached us
                port = "" if requested_url.port == PELITA_PORT or requested_url.port is None else f":{requested_url.port}"
                full_url = f"{requested_url.scheme}://{requested_url.hostname}{port}/{team_info.server_path}"
                avaliable_teams[full_url] = team_info.team_name

            avaliable_teams_json = json.dumps(avaliable_teams).encode("utf8")

            self.router_sock.send_multipart([dealer_id, avaliable_teams_json])

        elif "REQUEST" in msg_obj:
            # incoming message is a new request
            if len(self.connection_map) >= self.max_connections:
                _logger.warning("Exceeding maximum number of connections. Ignoring")
                self.router_sock.send_multipart([dealer_id, b"NOCONN"])
                return

            # TODO: Do not update status with every message

            requested_url = urlparse(msg_obj['REQUEST'])
            progress.console.log(f"Request from id {dealer_id.hex()}: {requested_url.scheme}://{requested_url.hostname}{requested_url.path}")

            if len(self.team_infos) == 0:
                self.router_sock.send_multipart([dealer_id, b"NOTEAM"])
                return

            # Select default team in case we don’t find any
            team = self.team_infos[0]
            for team_info in self.team_infos:
                if requested_url.path == '/' + team_info.server_path:
                    team = team_info
                    break
            else:
                # not found. use default but warn
                progress.console.print(f"Player for path {requested_url.path} not found. Using default.")

            info = GameInfo(round=None, max_rounds=None, my_index=0,
                            my_name="waiting", my_score=0,
                            enemy_name="waiting", enemy_score=0)
            task = progress.add_task(info.status(), total=info.max_rounds)


            num_running = len(self.connection_map)
            _logger.info(f"Starting match for team {team.spec}. ({num_running} already running.)")
            subproc, pair_sock = run_team_in_subprocess(self.ctx, team.spec, silent_bots=team.silent_bots)

            self.poll.register(pair_sock, zmq.POLLIN)

            process_info = ProcessInfo(proc=subproc, task=task, info=info, dealer_id=dealer_id, pair_socket=pair_sock)
            self.connection_map[process_info.dealer_id] = process_info
            self.connections_by_pair_socket[process_info.pair_socket] = process_info


            # Send a reply to the requester (that the process has started)
            # Otherwise they might already start querying for the team name
            self.router_sock.send_multipart([dealer_id, b"OK"])

        else:
            _logger.info("Unknown incoming DEALER and not a request.")


    def update_progress_bar(self, progress, process_info: ProcessInfo, force_exit=False):
        if not process_info.info.last_msg:
            return

        if process_info.info.finished:
            return

        try:
            msg_obj = json.loads(process_info.info.last_msg)
        except ValueError as e:
            progress.console.log(f"Error {e!r} when parsing incoming message. Ignoring.")
            _logger.warning(f"Error {e!r} when parsing incoming message. Ignoring.")
            return

        try:
            process_info.info.round = msg_obj['__data__']['game_state']['round']
            process_info.info.max_rounds = msg_obj['__data__']['game_state']['max_rounds']
        except KeyError:
            process_info.info.round = None

        if round is not None:
            progress.update(process_info.task, completed=process_info.info.round, total=process_info.info.max_rounds)

        try:
            process_info.info.my_index = msg_obj['__data__']['game_state']['team']['team_index']
            process_info.info.my_name = msg_obj['__data__']['game_state']['team']['name']
            process_info.info.my_score = msg_obj['__data__']['game_state']['team']['score']
            process_info.info.enemy_name = msg_obj['__data__']['game_state']['enemy']['name']
            process_info.info.enemy_score = msg_obj['__data__']['game_state']['enemy']['score']

            progress.update(process_info.task, description=process_info.info.status())
        except KeyError:
            pass

        try:
            is_exit = msg_obj['__action__'] == 'exit'
        except KeyError:
            is_exit = False

        if is_exit or force_exit:
            progress.stop_task(process_info.task)
            progress.update(process_info.task, visible=False)
            process_info.info.finished = True
            progress.console.print(process_info.info.status())


    def start(self):
        zc = zeroconf.Zeroconf()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
        ) as progress:

            if self.advertise:

                for team in self.team_infos:
                    info = zeroconf_register(zc, self.advertise, self.port, team.spec, team.server_path, print=progress.console.print)
                    if info:
                        self.team_serviceinfo_mapping[(team.spec, team.server_path)] = info

            while True:
                # If we have active connections, we break out every second
                # to update the status bar
                # Otherwise, we’ll just sleep
                poll_timeout = 1000 if len(self.connection_map) else None

                incoming_evts = dict(self.poll.poll(poll_timeout))
                has_router_sock = incoming_evts.pop(self.router_sock, None)

                if has_router_sock == zmq.POLLIN:
                    try:
                        dealer_id, message = self.router_sock.recv_multipart()

                        # check if we know the dealer already
                        if dealer_id in self.connection_map.keys():
                            # incoming message refers to an existing connection
                            self.handle_known_client(dealer_id, message, progress)

                        else:
                            # a new connection. we parse the message and check what we need to do
                            self.handle_new_connection(dealer_id, message, progress)

                    except Exception as e:
                        _logger.debug(f"Error {e!r} when handling incoming message {message}. Ignoring.")

                # Are there any non-router messages waiting for us?
                if len(incoming_evts):
                    # One or more of our spawned players has replied
                    # try to find the according process info
                    for socket in incoming_evts:
                        process_info = self.connections_by_pair_socket.get(socket)
                        if process_info:
                            # success
                            message = process_info.pair_socket.recv()
                            # route message back
                            self.router_sock.send_multipart([process_info.dealer_id, message])

                self.handle_send_queue()

                # not every event needs to update the progress bars
                if (now := time.monotonic()) - self.ticks_progressbar > 0.01:
                    self.ticks_progressbar = now
                    for process_info in list(self.connection_map.values()):
                        self.update_progress_bar(progress, process_info)

                if (now := time.monotonic()) - self.ticks_process_cleanup > 3:
                    self.ticks_process_cleanup = now
                    count = 0
                    for process_info in list(self.connection_map.values()):
                        # check if the process has terminated
                        if process_info.proc.poll() is not None:
                            self.update_progress_bar(progress, process_info, force_exit=True)
                            # We need to unregister the socket or else the polling will take longer and longer
                            self.poll.unregister(process_info.pair_socket)
                            del self.connection_map[process_info.dealer_id]
                            count += 1
                    if count:
                        plural = "" if count == 1 else "es"
                        progress.console.log(f"Cleaned up {count} process{plural}. ({len(self.connection_map)} still running.)")

def load_team_info(team_spec: str) -> Optional[TeamInfo]:
    # Takes a team_spec, tries to run it and returns a team info object

    # TODO: Improve path handling for manual override and duplicate detection

    team_name = _check_team(team_spec)
    if not team_name:
        pprint(f"Team {team_spec} did not return a filename. Skipping.")
        return

    team_info = TeamInfo(team_spec, team_name)

    team_path = team_name.replace(" ", "_")
    team_path = urllib.parse.quote(team_path)

    team_info.server_path = team_path
    pprint(f"Mapping team {team_info.spec} ({team_info.team_name}) to path {team_info.server_path}")
    return team_info

def run_team_in_subprocess(ctx, team_spec, silent_bots=False):
    pair_sock = ctx.socket(zmq.PAIR)
    port = pair_sock.bind_to_random_port('tcp://127.0.0.1')
    pair_addr = 'tcp://127.0.0.1:{}'.format(port)

    subproc = play_remote(team_spec, pair_addr, silent_bots=silent_bots)

    return subproc, pair_sock

# TODO: This could optionally run in a sandbox (systemd-run)
def play_remote(team_spec, pair_addr, silent_bots=False):
    external_call = [sys.executable,
                    '-m',
                    'pelita.scripts.pelita_player',
                    'remote-game',
                    team_spec,
                    pair_addr,
                    *(['--silent-bots'] if silent_bots else []),
                    ]
    _logger.debug("Executing: %r", external_call)
    sub = subprocess.Popen(external_call)
    return sub

# TODO: This could optionally run in a sandbox (systemd-run)
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

def configure(ctx, param, filename):
    if not filename:
        return
    settings = yaml.load(filename, Loader=yaml.SafeLoader)
    if 'teams' in settings:
        settings['teams'] = [team['spec'] for team in settings['teams'] if team.get('spec')]

    ctx.default_map = settings

@main.command(help="Start a pelita server with given players")
@click.option('--config',
              default=None,
              type=click.File('r'),
              help='Configuration file',
              callback=configure,
              is_eager=True,
              expose_value=False,
              show_default=True)
@click.option('--address', default="0.0.0.0")
@click.option('--port', default=PELITA_PORT)
@click.option('--team', 'teams', type=str, multiple=True, help="Team path")
@click.option('--advertise', default=None, type=str,
              help='advertise player on zeroconf')
@click.option('--max-connections', default=DEFAULT_MAX_CONNECTIONS, show_default=True,
              help='Maximum number of connections that we want to handle')
def remote_server(address, port, teams, advertise, max_connections):
    # When used with --config the following yaml format is expected:
    #
    #    address: 0.0.0.0
    #    port: 41736
    #    teams:
    #    - name: abc
    #      spec: pelita/player/StoppingPlayer
    #    - name: def
    #      spec: path/to/module

    rng = Random()

    session_key = "".join(str(rng.randint(0, 9)) for _ in range(12))
    pprint(f"Use --session-key {session_key} to for the admin API.")

    team_infos = []
    for team_spec in teams:
        team_info = load_team_info(team_spec)
        if team_info:
            team_infos.append(team_info)

    server = PelitaServer(team_infos, address, port, advertise=advertise, session_key=session_key,
                          max_connections=max_connections)
    server.start()

    # asyncio repl …
    # reload via zqm key

def send_api_message(url, session_key, type, subtype, **payload):
    ctx = zmq.Context()
    sock = ctx.socket(zmq.DEALER)
    parsed_url = urlparse(url)

    if parsed_url.scheme not in ['pelita', 'tcp'] :
        raise ValueError('Scheme must be pelita or tcp')

    address = parsed_url.hostname
    port = parsed_url.port or PELITA_PORT

    sock.connect(f"tcp://{address}:{port}")
    sock.send_json({
        type: subtype,
        'key': session_key,
        **payload
    })


@main.command(help="Show server statistics")
@click.option('--url', default="pelita://localhost/")
@click.option('--session-key', type=str, required=True)
def show_statistics(url, session_key):
    send_api_message(url, session_key, "STATUS", "show-stats")

@main.command(help="Add team")
@click.argument('team_spec')
@click.option('--url', default="pelita://localhost/")
@click.option('--session-key', type=str, required=True)
def add_team(url, session_key, team_spec):
    send_api_message(url, session_key, "TEAM", "ADD", team_spec=team_spec)


if __name__ == '__main__':
    main()
