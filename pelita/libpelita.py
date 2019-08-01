#!/usr/bin/env python3

from collections import namedtuple
import contextlib
import io
import json
import logging
import os
from pathlib import Path
import shlex
import signal
import subprocess
import sys
import tempfile
from tempfile import TemporaryFile
import uuid

import zmq

from .player.team import make_team

_logger = logging.getLogger(__name__)
_mswindows = (sys.platform == "win32")

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


def start_logging(filename, module='pelita'):
    if not filename or filename == '-':
        hdlr = logging.StreamHandler()
    else:
        hdlr = logging.FileHandler(filename, mode='w')
    logger = logging.getLogger(module)
    FORMAT = '[%(relativeCreated)06d %(name)s:%(levelname).1s][%(funcName)s] %(message)s'
    formatter = logging.Formatter(FORMAT)
    hdlr.setFormatter(formatter)
    logger.addHandler(hdlr)
    logger.setLevel(logging.DEBUG)


class ModuleRunner:
    def __init__(self, team_spec):
        self.team_spec = team_spec

class DefaultRunner(ModuleRunner):
    def call_args(self, addr):
        player = 'pelita.scripts.pelita_player'
        external_call = [get_python_process(),
                         '-m',
                         player,
                         self.team_spec,
                         addr,
                         '--color',
                         self.color]
        return external_call

class BinRunner(ModuleRunner):
    def call_args(self, addr):
        external_call = [self.team_spec,
                         addr]
        return external_call

@contextlib.contextmanager
def _call_pelita_player(module_spec, address, color='', dump=None):
    """ Context manager version of `call_pelita_player`.

    Runs `call_pelita_player` as long as the `with` statement is executed
    and automatically terminates it afterwards. This is useful, if one
    just needs to send a few commands to a player.
    """

    proc = None
    try:
        proc, stdout, stderr = call_pelita_player(module_spec, address, color, dump)
        yield proc
    except KeyboardInterrupt:
        pass
    finally:
        # we close stdout, stderr before terminating
        # this hopefully means that it will do some flushing
        if stdout:
            stdout.close()
        if stderr:
            stderr.close()
        if proc is None:
            print("Problem running pelita player.")
        else:
            _logger.debug("Terminating proc %r", proc)
            proc.terminate()
            proc.wait()
            _logger.debug("%r terminated.", proc)


def call_pelita_player(module_spec, address, color='', dump=None):
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
    runner_inst = runner(module_spec.module)
    runner_inst.color = color
    call_args = runner_inst.call_args(address)
    _logger.debug("Executing: %r", call_args)
    if dump:
        stdout = Path(dump + '.' + (color or module_spec) + '.out').open('w')
        stderr = Path(dump + '.' + (color or module_spec) + '.err').open('w')
        return (subprocess.Popen(call_args, stdout=stdout, stderr=stderr), stdout, stderr)
    else:
        return (subprocess.Popen(call_args), None, None)


@contextlib.contextmanager
def run_and_terminate_process(args, **kwargs):
    """ This serves as a contextmanager around `subprocess.Popen`, ensuring that
    after the body of the with-clause has finished, the process itself (and the
    process’s children) terminates as well.

    On Unix we try sending a SIGTERM before killing the process group but as
    afterwards we only wait on the first child, this means that the grand children
    do not get the chance to properly terminate.
    In cases where the first child has children that should properly close, the
    first child should catch SIGTERM with a signal handler and wait on its children.

    On Windows we send a CTRL_BREAK_EVENT to the whole process group and
    hope for the best. :)
    """

    _logger.debug("Executing: {}".format(shlex_unsplit(args)))

    try:
        if _mswindows:
            p = subprocess.Popen(args, **kwargs, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        else:
            p = subprocess.Popen(args, **kwargs, preexec_fn=os.setsid)
        yield p
    finally:
        if _mswindows:
            _logger.debug("Sending CTRL_BREAK_EVENT to {proc} with pid {pid}.".format(proc=p, pid=p.pid))
            os.kill(p.pid, signal.CTRL_BREAK_EVENT)
        else:
            try:
                pgid = os.getpgid(p.pid)
                _logger.debug("Sending SIGTERM to pgid {pgid}.".format(pgid=pgid))
                os.killpg(pgid, signal.SIGTERM) # send sigterm, or ...
                try:
                    # It would be nicer to wait with os.waitid on the process group
                    # but that does not seem to exist on macOS.
                    p.wait(3)
                except subprocess.TimeoutExpired:
                    _logger.debug("Sending SIGKILL to pgid {pgid}.".format(pgid=pgid))
                    os.killpg(pgid, signal.SIGKILL) # send sigkill, or ...
            except ProcessLookupError:
                # did our process group vanish?
                # we try killing only the child process then
                _logger.debug("Sending SIGTERM to pid {pid}.".format(pid=p.pid))
                p.terminate()
                try:
                    p.wait(3)
                except subprocess.TimeoutExpired:
                    _logger.debug("Sending SIGKILL to pid {pid}.".format(pid=p.pid))
                    p.kill()


def call_pelita(team_specs, *, rounds, filter, viewer, seed, write_replay=False, store_output=False):
    """ Starts a new process with the given command line arguments and waits until finished.

    Returns
    =======
    tuple of (game_state, stdout, stderr)
    """
    team1, team2 = team_specs

    ctx = zmq.Context()
    reply_sock = ctx.socket(zmq.PAIR)

    if os.name.upper() == 'POSIX':
        filename = 'pelita-reply.{uuid}'.format(pid=os.getpid(), uuid=uuid.uuid4())
        path = os.path.join(tempfile.gettempdir(), filename)
        reply_addr = 'ipc://' + path
        reply_sock.bind(reply_addr)
    else:
        addr = 'tcp://127.0.0.1'
        reply_port = reply_sock.bind_to_random_port(addr)
        reply_addr = 'tcp://127.0.0.1' + ':' + str(reply_port)

    rounds = ['--rounds', str(rounds)] if rounds else []
    filter = ['--filter', filter] if filter else []
    viewer = ['--' + viewer] if viewer else []
    seed = ['--seed', seed] if seed else []
    write_replay = ['--write-replay', write_replay] if write_replay else []
    store_output = ['--store-output', store_output] if store_output else []

    cmd = [get_python_process(), '-m', 'pelita.scripts.pelita_main',
           team1, team2,
           '--reply-to', reply_addr,
           *rounds,
           *filter,
           *viewer,
           *seed,
           *write_replay,
           *store_output]

    # We need to run a process in the background in order to await the zmq events
    # stdout and stderr are written to temporary files in order to be more portable
    with TemporaryFile(mode='w+t') as stdout_buf, TemporaryFile(mode='w+t') as stderr_buf:
        # We use the environment variable PYTHONUNBUFFERED here to retrieve stdout without buffering
        with run_and_terminate_process(cmd, stdout=stdout_buf, stderr=stderr_buf,
                                            universal_newlines=True,
                                            env=dict(os.environ, PYTHONUNBUFFERED='x')) as proc:

            poll = zmq.Poller()
            poll.register(reply_sock, zmq.POLLIN)

            final_game_state = None

            while True:
                evts = dict(poll.poll(1000))

                if not evts and proc.poll() is not None:
                    # no more events and proc has finished.
                    # we break the loop
                    break

                socket_ready = evts.get(reply_sock, False)
                if socket_ready:
                    try:
                        game_state = json.loads(reply_sock.recv_string())
                        finished = game_state.get("gameover", None)
                        whowins = game_state.get("whowins", None)
                        if finished:
                            final_game_state = game_state
                            break
                    except ValueError:  # JSONDecodeError
                        pass
                    except KeyError:
                        pass

        stdout_buf.seek(0)
        stderr_buf.seek(0)
        return (final_game_state, stdout_buf.read(), stderr_buf.read())


def check_team(team_spec):
    """ Instanciates a team from a team_spec and returns its name """
    team, _zmq_context = make_team(team_spec)
    return team.team_name


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
        # we close stdout, stderr before terminating
        # this hopefully means that it will do some flushing
        for (sp, stdout, stderr) in subprocesses:
            if stdout:
                stdout.close()
            if stderr:
                stderr.close()
        # kill all client processes. NOW!
        # (is ths too early?)
        for (sp, stdout, stderr) in subprocesses:
            _logger.debug("Attempting to terminate %r.", sp)
            sp.terminate()
        for (sp, stdout, stderr) in subprocesses:
            sp.wait()
            _logger.debug("%r terminated.", sp)
