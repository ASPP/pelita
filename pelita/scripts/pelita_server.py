#!/usr/bin/env python3

from dataclasses import dataclass
import json
import logging
import random
import signal
import subprocess
import sys
import time
from typing import Optional, Dict
from urllib.parse import urlparse
from weakref import WeakValueDictionary

import click
from rich import print as pprint
from rich.progress import Progress, SpinnerColumn, TaskProgressColumn, BarColumn, TextColumn, TimeElapsedColumn, Task
import zeroconf
import zmq

from ..network import PELITA_PORT
from .script_utils import start_logging

_logger = logging.getLogger(__name__)

zeroconf.log.setLevel(logging.INFO)
zeroconf.log.addHandler(_logger)

MAX_CONNECTIONS = 100

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

def with_zmq_router(team_specs, address, port, *, advertise: str, session_key: str, show_progress: bool = True):
    # TODO: Explain how ROUTER-DEALER works with ZMQ

    # maps socket/process/game data
    connection_map: Dict[bytes, ProcessInfo] = {}
    connections_by_pair_socket = WeakValueDictionary() # automatic cache

    # maps team_spec, path to zc.ServiceInfo
    team_serviceinfo_mapping = {}

    def cleanup(signum, frame):
        for process_info in connection_map.values():
            _logger.warn(f"Cleaning up unfinished process: {process_info.proc}.")
            process_info.proc.terminate()
        finish_time = time.monotonic() + 3
        for process_info in connection_map.values():
            # We need to wait for all processes to finish
            # Otherwise we might exit before the signal has been sent
            _logger.debug(f"Waiting for process {process_info.proc} to terminate")
            remainder = finish_time - time.monotonic()
            if remainder > 0:
                try:
                    process_info.proc.wait(remainder)
                except subprocess.TimeoutExpired:
                    _logger.warn(f"Process {process_info.proc} has not finished.")

        sys.exit()

    signal.signal(signal.SIGTERM, cleanup)
    signal.signal(signal.SIGINT, cleanup)

    ctx = zmq.Context()
    router_sock = ctx.socket(zmq.ROUTER)
    router_sock.bind(f"tcp://{address}:{port}")

    poll = zmq.Poller()
    poll.register(router_sock, zmq.POLLIN)

    # TODO handle show_progress

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
    ) as progress:

        if advertise:
            zc = zeroconf.Zeroconf()
            for team_spec, path in team_specs:
                info = zeroconf_register(zc, advertise, port, team_spec, path, print=progress.console.print)
                if info:
                    team_serviceinfo_mapping[(team_spec, path)] = info

        while True:
            incoming_evts = dict(poll.poll(1000))
            has_router_sock = incoming_evts.pop(router_sock, None)

            if has_router_sock:
                dealer_id, msg = router_sock.recv_multipart()

                try:
                    # check if we know the dealer already
                    if dealer_id in connection_map.keys():
                        # incoming message refers to an existing connection


                        # We must check for existence of the value, because it could have been
                        # garbage-collected after the elif check
                        process_info = connection_map.get(dealer_id)
                        if process_info is None:
                            continue

                        task = process_info.task
                        info = process_info.info
                        pair_socket = process_info.pair_socket

                        # TODO: we do not want to do this every millisecond

                        try:
                            msg_obj = json.loads(msg)
                        except ValueError as e:
                            # TODO should not continue
                            progress.console.log(f"Error {e!r} when parsing incoming message. Ignoring.")
                            _logger.warn(f"Error {e!r} when parsing incoming message. Ignoring.")
                            continue

                        try:
                            is_exit = msg_obj['__action__'] == 'exit'
                        except KeyError:
                            is_exit = False

                        if is_exit:
                            progress.stop_task(task)
                            progress.update(task, visible=False)
                            info.finished = True
                            progress.console.print(info.status())

                        try:
                            info.round = msg_obj['__data__']['game_state']['round']
                            info.max_rounds = msg_obj['__data__']['game_state']['max_rounds']
                        except KeyError:
                            info.round = None

                        if round is not None:
                            progress.update(task, completed=info.round, total=info.max_rounds)

                        try:
                            info.my_index = msg_obj['__data__']['game_state']['team']['team_index']
                            info.my_name = msg_obj['__data__']['game_state']['team']['name']
                            info.my_score = msg_obj['__data__']['game_state']['team']['score']
                            info.enemy_name = msg_obj['__data__']['game_state']['enemy']['name']
                            info.enemy_score = msg_obj['__data__']['game_state']['enemy']['score']

                            progress.update(task, description=info.status())
                        except KeyError:
                            pass

                        pair_socket.send(msg)

                    else:
                        # a new connection. we parse the message and check what we need to do

                        try:
                            msg_obj = json.loads(msg)
                        except ValueError as e:
                            # TODO should not continue
                            progress.console.log(f"Error {e!r} when parsing incoming message. Ignoring.")
                            _logger.warn(f"Error {e!r} when parsing incoming message. Ignoring.")
                            continue

                        # TODO actions
                        # stop server - do not accept new requests
                        # purge server - drop all running connections

                        if "STATUS" in msg_obj:
                            # check key
                            if not msg_obj.get('key', None) == session_key:
                                continue

                            progress.console.print("TODO: Status information")

                        elif "TEAM" in msg_obj:
                            # check key
                            if not msg_obj.get('key', None) == session_key:
                                continue

                            team_spec = msg_obj.get('team')
                            path = msg_obj.get('path')

                            if msg_obj.get('TEAM') == 'ADD':
                                info = zeroconf_register(zc, advertise, port, team_spec, path, print=progress.console.print)
                                if info:
                                    team_serviceinfo_mapping[(team_spec, path)] = info

                            if msg_obj.get('TEAM') == 'REMOVE':
                                info = team_serviceinfo_mapping[(team_spec, path)]
                                zeroconf_deregister(zc, info)

                        elif "REQUEST" in msg_obj:
                            if len(connection_map) >= MAX_CONNECTIONS:
                                _logger.warn("Exceeding maximum number of connections. Ignoring")
                                continue

                            # TODO: Send a reply to the requester (when the process has started?).
                            # Otherwise they might already start querying for the team name

                            # TODO: Do not update status with every message

                            requested_url = urlparse(msg_obj['REQUEST'])
                            progress.console.log(f"Request {requested_url.path} for dealer {dealer_id}")

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

                            # incoming message is a new request
                            pair_sock = ctx.socket(zmq.PAIR)
                            port = pair_sock.bind_to_random_port('tcp://127.0.0.1')
                            pair_addr = 'tcp://127.0.0.1:{}'.format(port)

                            poll.register(pair_sock, zmq.POLLIN)

                            num_running = len(connection_map)
                            _logger.info(f"Starting match for team {team_specs}. ({num_running} already running.)")
                            subproc = play_remote(team_spec, pair_addr, silent=show_progress)

                            process_info = ProcessInfo(proc=subproc, task=task, info=info, dealer_id=dealer_id, pair_socket=pair_sock)
                            connection_map[process_info.dealer_id] = process_info
                            connections_by_pair_socket[process_info.pair_socket] = process_info

                        else:
                            _logger.info("Unknown incoming DEALER and not a request.")

                except Exception as e:
                    _logger.warn(f"Error {e!r} when handling incoming message {msg}. Ignoring.")

            # Are there any non-router messages waiting for us?
            if len(incoming_evts):
                # One or more of our spawned players has replied
                # try to find the according process info
                for socket in incoming_evts:
                    process_info = connections_by_pair_socket.get(socket)
                    if process_info:
                        # success

                        msg = process_info.pair_socket.recv()
                        # route message back
                        router_sock.send_multipart([process_info.dealer_id, msg])

            # TODO: Only do this every few seconds
            count = 0
            for process_info in list(connection_map.values()):
                # check if the process has terminated
                if process_info.proc.poll() is not None:
                    # We need to unregister the socket or else the polling will take longer and longer
                    poll.unregister(process_info.pair_socket)
                    del connection_map[process_info.dealer_id]
                    count += 1
            if count:
                progress.console.log("Cleaned up {} process(es). ({} still running.)".format(count, len(connection_map)))


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


@main.command(help="Run pelita server with given players")
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
@click.option('--url', default="pelita://localhost/")
@click.option('--session-key', type=str, required=True)
@click.option('--team', '-t', 'team', type=(str, str), required=True, help="Team path")
def add_team(url, session_key, team):
    team_spec, path = team
    send_api_message(url, session_key, "TEAM", "ADD", team=team_spec, path=path)


if __name__ == '__main__':
    main()
