#!/usr/bin/env python3

import contextlib
import hashlib
import importlib
import json
import logging
import sys
from pathlib import Path

import click
import zmq

from ..network import json_default_handler
from ..team import Team
from .script_utils import start_logging

_logger = logging.getLogger(__name__)

# Maximum time that a player will wait for a move request
# Note that this means that a player will exit when a game has been paused for one hour
TIMEOUT_SECS = 60 * 60

@contextlib.contextmanager
def with_sys_path(dirname):
    sys.path.insert(0, dirname)
    try:
        yield
    finally:
        sys.path.remove(dirname)

def run_player(team_spec, address, team_name_override=False, silent_bots=False):
    """ Creates a team from `team_spec` and runs
    a game through the zmq PAIR socket on `address`.

    Parameters
    ----------
    team_spec : str
        path to the module that declares the team
    address : address to zmq PAIR socket
        the address of the remote team socket

    """
    # Connect to the given address
    context = zmq.Context()
    socket = context.socket(zmq.PAIR)
    poller = zmq.Poller()
    poller.register(socket, flags=zmq.POLLIN)

    try:
        socket.connect(address)
    except zmq.ZMQError as e:
        raise IOError(f"Failed to connect the client to address {address}: {e}")

    try:
        team = load_team(team_spec)
        _logger.info(f"Running player '{team_spec}' ({team.team_name})")

    except Exception as e:
        # We could not load the team.
        # Send an error to the server

        error = {
            '__error__': e.__class__.__name__,
            '__error_msg__': f'Could not load {team_spec}: {e}',
        }

        socket.send_json(error)
        # TODO: Exit with a status code?
        return False

    data = {
        'team_name': team.team_name,
    }
    socket.send_json({'__status__': 'ok', '__data__': data})

    while True:
        cont = player_handle_request(socket, poller, team, team_name_override=team_name_override, silent_bots=silent_bots)
        if not cont:
            return


def player_handle_request(socket, poller, team, team_name_override=False, silent_bots=False):
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
        socks = dict(poller.poll(timeout=TIMEOUT_SECS * 1000))
        if socks.get(socket) == zmq.POLLIN:
            json_message = socket.recv_unicode()
        else:
            # TODO: Would be nice to tell Pelita main that we’re exiting
            _logger.warning(f"No request in {TIMEOUT_SECS} seconds. Exiting player.")

            # returning False breaks the loop
            return False
    except Exception:
        # Exit without sending a value back on the socket
        return True

    try:
        py_obj = json.loads(json_message)
        msg_id = py_obj.get("__uuid__") # if an uuid is given, we must reply with a value
        action = py_obj["__action__"]
        data = py_obj["__data__"]
        _logger.debug("<o-- %r [%s]", action, msg_id)

        # feed client actor here …
        if action == "set_initial":
            retval = team.set_initial(**data)
        elif action == "get_move":
            retval = team.get_move(**data)
            if silent_bots:
                try:
                    del retval['say']
                except KeyError:
                    pass

        elif action == "team_name":
            if isinstance(team_name_override, str):
                retval = team_name_override
            else:
                retval = team.team_name
            # TODO: Log team name override
        elif action == "exit":
            # quit.
            # This could be an opportunity to send data back to the main Pelita process
            _logger.info("Got exit request. Shutting down the player.")
            reply = None
            return False
        else:
            _logger.warning(f"Player received unknown action {action}.")

        reply = {
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
        reply = {
            '__error__': e.__class__.__name__
        }
        return True

    except Exception as e:
        # All client exceptions should have been caught in the
        # team class. This clause is a safety net for
        # exceptions that are not caused by a bot.

        msg = "Exception in client code for team %s." % team
        print(msg, file=sys.stderr)
        reply = {
            '__uuid__': msg_id,
            '__error__': e.__class__.__name__,
            '__error_msg__': str(e)
        }
        return False

    finally:
        if reply is None:
            return
        if msg_id is not None:
            # we use our own json_default_handler
            # to automatically convert numpy ints to json
            json_message = json.dumps(reply, default=json_default_handler)
            # return the message
            socket.send_unicode(json_message)
            match reply:
                case {'__error__': err, '__uuid__': msg_id}:
                    _logger.warning("o-!> %r [%s]", err, msg_id)
                case {'__return__': retval, '__uuid__': msg_id}:
                    _logger.debug("o--> %r [%s]", retval, msg_id)
                case _:
                    raise RuntimeError("Created bad reply message")


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
    module_path = Path(path)

    if not module_path.parent.exists():
        raise FileNotFoundError("Folder {} does not exist.".format(module_path.parent))

    dirname = str(module_path.parent)
    modname = module_path.stem

    if modname in sys.modules:
        raise ValueError("A module named ‘{}’ has already been imported.".format(modname))

    with with_sys_path(dirname):
        module = importlib.import_module(modname)

    return team_from_module(module)


def team_from_module(module):
    """ Looks for a move function and a team name in
    `module` and returns a team.

    Raises
    ------
    TypeError
        move not a function or TEAM_NAME not a string
    AttributeError
        no move or no TEAM_NAME attribute

    """
    # look for a new-style team
    move = module.move
    name = module.TEAM_NAME

    if not callable(move):
        raise TypeError("move is not a function")
    if not isinstance(name, str):
        raise TypeError("TEAM_NAME is not a string")

    team = Team(move, team_name=name)
    return team


@click.group()
@click.option('--log',
              is_flag=False, flag_value="-", default=None, metavar='LOGFILE',
              help="print debugging log information to LOGFILE (default 'stderr')")
def main(log):
    if log is not None:
        start_logging(log)


@main.command(help="Load team and connect to the specified address.")
@click.argument('team')
@click.argument('address')
@click.option('--team-name-override',
              default=None,
              help='Override the team name')
@click.option('--silent-bots',
              is_flag=True,
              default=False,
              help='Filter bot speak')
def remote_game(team, address, team_name_override, silent_bots):
    run_player(team, address, team_name_override=team_name_override, silent_bots=silent_bots)


@main.command("check-team", help="Load team and print its name.")
@click.argument('team')
def cli_check_team(team):
    return check_team(team)

@main.command("hash-team", help="Load team and print its hash.")
@click.argument('team')
def cli_hash_team(team):
    print(hash_team(team))

def check_team(team):
    print(load_team(team).team_name)

def hash_team(team):
    # Load the team so that we have the modules ready
    load_team(team)

    folder = Path(team).parent.resolve()
    modules = []
    for name, module in sys.modules.items():
        if hasattr(module, '__file__') and module.__file__:
            path = Path(module.__file__)
            if path.is_relative_to(folder):
                modules.append([name, path])

    _logger.debug(f"Hashing module {team}")

    # sort relative paths by module name and generate our sha
    sha1 = hashlib.sha1()
    for module, path in sorted(modules):
        _logger.debug(f"Hashing {team}: Adding {module}")
        sha1.update(path.read_bytes())
    res = sha1.hexdigest()
    _logger.debug(f"SHA1 for {team}: {res}.")
    return res


if __name__ == '__main__':
    main()
