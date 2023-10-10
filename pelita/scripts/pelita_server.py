#!/usr/bin/env python3

from dataclasses import dataclass
import logging
import random
import signal
import subprocess
import sys
import time
from typing import Optional
from urllib.parse import urlparse

import click
from rich import print as pprint
from rich.progress import Progress
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
        plural = "s" if (self.round is not None and self.round > 1) else ""
        finished = f"[b]Finished[/b] ({self.round} round{plural}): " if self.finished else ""
        if self.my_index == 0:
            return f"{finished}[u]{self.my_name} ({self.my_score})[/u] vs {self.enemy_name} ({self.enemy_score})"
        else:
            return f"{finished}{self.enemy_name} ({self.enemy_score}) vs [u]{self.my_name} ({self.my_score})[/u]"


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
            'path': '/' + path,
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
            _logger.warn(f"Cleaning up unfinished process: {proc}.")
            proc.terminate()
        finish_time = time.monotonic() + 3
        for proc in proc_dealer_mapping:
            # We need to wait for all processes to finish
            # Otherwise we might exit before the signal has been sent
            _logger.debug(f"Waiting for process {proc} to terminate")
            remainder = finish_time - time.monotonic()
            if remainder > 0:
                try:
                    proc.wait(remainder)
                except subprocess.TimeoutExpired:
                    _logger.warn(f"Process {proc} has not finished.")

        sys.exit()

    signal.signal(signal.SIGTERM, cleanup)
    signal.signal(signal.SIGINT, cleanup)

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

if __name__ == '__main__':
    main()
