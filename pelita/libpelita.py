#!/usr/bin/env python3

from collections import namedtuple
import contextlib
import logging
import os
import shlex
import subprocess
import sys

import zmq

from .simplesetup import RemoteTeamPlayer, SimpleController, SimplePublisher, SimpleServer

_logger = logging.getLogger("pelita.libpelita")

TeamSpec = namedtuple("TeamSpec", ["module", "address"])
ModuleSpec = namedtuple("ModuleSpec", ["prefix", "module"])


def get_python_process():
    py_proc = sys.executable
    if not py_proc:
        raise RuntimeError("Cannot retrieve current Python executable.")
    return py_proc


def shlex_unsplit(cmd):
    """
    Translates a list of command arguments into bash-like ‘human’ readable form.
    Pseudo-reverses shlex.split()

    Example
    -------
        >>> shlex_unsplit(["command", "-f", "Hello World"])
        "command -f 'Hello World'"

    Parameters
    ----------
    cmd : list of string
        command + parameter list

    Returns
    -------
    string
    """
    return " ".join(shlex.quote(arg) for arg in cmd)


def firstNN(*args):
    """
    Return the first argument not None.

    Example
    -------
        >>> firstNN(None, False, True)
        False
        >>> firstNN(True, False, True)
        True
        >>> firstNN(None, None, True)
        True
        >>> firstNN(None, 2, True)
        2
        >>> firstNN(None, None, None)
        None
        >>> firstNN()
        None
    """
    return next(filter(lambda x: x is not None, args), None)



class ModuleRunner:
    def __init__(self, team_spec):
        self.team_spec = team_spec

class DefaultRunner(ModuleRunner):
    def run(self, addr):
        player = 'pelita.scripts.pelita_player'
        external_call = [get_python_process(),
                         '-m',
                         player,
                         self.team_spec,
                         addr]
        _logger.debug("Executing: %r", external_call)
        return subprocess.Popen(external_call)

class BinRunner(ModuleRunner):
    def run(self, addr):
        external_call = [self.team_spec,
                         addr]
        _logger.debug("Executing: %r", external_call)
        return subprocess.Popen(external_call)

@contextlib.contextmanager
def _call_standalone_pelitagame(module_spec, address):
    proc = None
    try:
        proc = call_standalone_pelitagame(module_spec, address)
        yield proc
    finally:
        if proc is None:
            print("Problem running pelitagame")
        else:
            _logger.debug("Terminating proc %r", proc)
            proc.terminate()

def call_standalone_pelitagame(module_spec, address):
    """ Starts another process with the same Python executable,
    the same start script (pelitagame) and runs `team_spec`
    as a standalone client on URL `addr`.
    """
    defined_runners = {
        "py": DefaultRunner,
        "bin": BinRunner,
    }

    if module_spec.prefix is not None:
        try:
            runner = defined_runners[module_spec.prefix]
        except KeyError:
            raise ValueError("Unknown runner: {}:".format(module_spec.prefix))
    else:
        runner = DefaultRunner
    return runner(module_spec.module).run(address)

def check_team(team_spec):
    ctx = zmq.Context()
    socket = ctx.socket(zmq.PAIR)

    if team_spec.module is None:
        _logger.info("Binding zmq.PAIR to %s", team_spec.address)
        socket.bind(team_spec.address)

    else:
        _logger.info("Binding zmq.PAIR to %s", team_spec.address)
        socket_port = socket.bind_to_random_port(team_spec.address)
        team_spec = team_spec._replace(address="%s:%d" % (team_spec.address, socket_port))

    team_player = RemoteTeamPlayer(socket)

    if team_spec.module:
        with _call_standalone_pelitagame(team_spec.module, team_spec.address):
            name = team_player.team_name()
    else:
        name = team_player.team_name()

    return name

def strip_module_prefix(module):
    if "@" in module:
        try:
            prefix, module = module.split("@")
            return ModuleSpec(prefix=prefix, module=module)
        except ValueError:
            raise ValueError("Bad module definition: {}.".format(module))
    else:
        return ModuleSpec(prefix=None, module=module)

def prepare_team(team_spec):
    # check if we've been given an address which a remote
    # player wants to connect to
    if "://" in team_spec:
        module = None
        address = team_spec
    else:
        module = strip_module_prefix(team_spec)
        address = "tcp://127.0.0.1"
    return TeamSpec(module, address)

def run_game(team_specs, game_config, viewers=None, controller=None):
    if viewers is None:
        viewers = []

    teams = [prepare_team(team_spec) for team_spec in team_specs]

    server = SimpleServer(layout_string=game_config["layout_string"],
                          rounds=game_config["rounds"],
                          bind_addrs=[team.address for team in teams],
                          initial_delay=game_config["initial_delay"],
                          max_timeouts=game_config["max_timeouts"],
                          timeout_length=game_config["timeout_length"],
                          layout_name=game_config["layout_name"],
                          seed=game_config["seed"])

    # Update our teams with the bound addresses
    teams = [
        team._replace(address=address)
        for team, address in zip(teams, server.bind_addresses)
    ]

    for idx, team in enumerate(teams):
        if team.module is None:
            print("Waiting for external team %d to connect to %s." % (idx, team.address))

    external_players = [
        call_standalone_pelitagame(team.module, team.address)
        for team in teams
        if team.module
    ]

    for viewer in viewers:
        server.game_master.register_viewer(viewer)

    if game_config.get("publisher"):
        server.game_master.register_viewer(game_config["publisher"])

    with autoclose_subprocesses(external_players):
        if controller is not None:
            if controller.game_master is None:
                controller.game_master = server.game_master
            controller.run()
            server.exit_teams()
        else:
            server.run()
        return server.game_master.game_state

@contextlib.contextmanager
def tk_viewer(publish_to=None, geometry=None, delay=None):
    if publish_to is None:
        publish_to = "tcp://127.0.0.1:*"
    publisher = SimplePublisher(publish_to)
    controller = SimpleController(None, "tcp://127.0.0.1:*")

    viewer = run_external_viewer(publisher.socket_addr, controller.socket_addr,
                                 geometry=geometry, delay=delay)
    yield { "publisher": publisher, "controller": controller }


@contextlib.contextmanager
def channel_setup(publish_to=None, reply_to=None):
    if publish_to is None:
        publish_to = "tcp://127.0.0.1:*"
    publisher = SimplePublisher(publish_to)
    controller = SimpleController(None, "tcp://127.0.0.1:*", reply_to=reply_to)

    yield { "publisher": publisher, "controller": controller }


def run_external_viewer(subscribe_sock, controller, geometry, delay):
    # Something on OS X prevents Tk from running in a forked process.
    # Therefore we cannot use multiprocessing here. subprocess works, though.
    viewer_args = [ str(subscribe_sock) ]
    if controller:
        viewer_args += ["--controller-address", str(controller)]
    if geometry:
        viewer_args += ["--geometry", "{0}x{1}".format(*geometry)]
    if delay:
        viewer_args += ["--delay", str(delay)]

    tkviewer = 'pelita.scripts.pelita_tkviewer'
    external_call = [get_python_process(),
                     '-m',
                     tkviewer] + viewer_args
    _logger.debug("Executing: %r", external_call)
    return subprocess.Popen(external_call)

@contextlib.contextmanager
def autoclose_subprocesses(subprocesses):
    """
    Automatically close subprocesses when the context ends.
    This needs to be done to shut down misbehaving bots
    when the main program finishes.
    """
    try:
        yield
    except KeyboardInterrupt:
        pass
    finally:
        # kill all client processes. NOW!
        # (is ths too early?)
        for sp in subprocesses:
            _logger.debug("Attempting to terminate %r.", sp)
            sp.terminate()
        for sp in subprocesses:
            sp.wait()
            _logger.debug("%r terminated.", sp)
