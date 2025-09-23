#!/usr/bin/env python3

import argparse
import json
import logging
import random
import sys
from pathlib import Path
from urllib.parse import urlparse

import zmq
from rich.console import Console
from rich.prompt import Prompt

import pelita
from pelita.network import PELITA_PORT
# TODO: The check_team option
from pelita.tournament import check_team

from .script_utils import start_logging

# silence stupid warnings from logging module
logging.root.manager.emittedNoHandlerWarning = 1
_logger = logging.getLogger(__name__)


def scan(team_spec):
    if team_spec != "SCAN":
        return team_spec
    from queue import Empty, Queue

    from zeroconf import ServiceBrowser, ServiceStateChange, Zeroconf

    SCAN_TIME = 5 # seconds

    q = Queue(maxsize=20)

    def on_service_state_change(
        zeroconf: Zeroconf, service_type: str, name: str, state_change: ServiceStateChange
    ) -> None:

        if state_change is ServiceStateChange.Added:
            info = zeroconf.get_service_info(service_type, name)

            def make_url(addr, port):
                if port == PELITA_PORT:
                    return f"pelita://{addr}"
                else:
                    return f"pelita://{addr}:{port}"

            if info:
                addresses = [make_url(addr, info.port) for addr in info.parsed_scoped_addresses()]

                team_name = info.properties[b"team_name"].decode()
                path = info.properties[b"path"].decode()
                q.put((addresses[0] + path, team_name), timeout=5)

    zeroconf = Zeroconf()
    services = ["_pelita-player._tcp.local."]
    console = Console()

    console.print(f"[bold]Remote player requested. Scanning network for players ({SCAN_TIME}s).")
    with console.status("[red bold]Searching for other players …") as _status:
        try:
            _browser = ServiceBrowser(zeroconf, services, handlers=[on_service_state_change])
            players = []
            import time
            start = time.monotonic()
            while start + 5 > time.monotonic():
                time.sleep(0.2)
                (addr, team_name) = q.get(timeout=5)
                #  if not players:
                    #console.print("[bold]Found players:")
                console.print(f"  [blue]{len(players)})[/] {team_name} \\[[blue]{addr}[/]]", highlight=False)
                players.append(f"{addr}")
        except Empty:
            pass
        except KeyboardInterrupt:
            return None
        finally:
            zeroconf.close()
    if players:
        console.print("  [blue]r)[/] Random team")
        console.print("  [blue]x)[/] Exit")
        console.print()
        console.print(f"Found {len(players)} player{'s' if len(players) != 1 else ''}.")

        choices = {str(i): player for i, player in enumerate(players)}

        answer = Prompt.ask("[bold]Select player to play against (r for random, x to exit)",
                            choices=list(choices) + ["r", "x"],
                            default="r")

        if answer == "r":
            console.print("Choosing random player.")
            return random.choice(players)
        elif answer in choices.keys():
            console.print(f"Choosing [blue]{choices[answer]}[/]", highlight=False)
            return choices[answer]
        else:
            return None


def scan_server(team_spec):
    parsed_url = urlparse(team_spec)
    if parsed_url.port:
        port = parsed_url.port
    else:
        port = PELITA_PORT

    send_addr = f"tcp://{parsed_url.hostname}:{port}"

    zmq_context = zmq.Context()
    socket = zmq_context.socket(zmq.DEALER)
    socket.setsockopt(zmq.LINGER, 0)
    socket.connect(send_addr)
    socket.send_json({"SCAN": team_spec})

    console = Console()

    console.print("[bold]Remote player requested. Scanning server for players.")

    WAIT_TIMEOUT = 5000
    incoming = socket.poll(timeout=WAIT_TIMEOUT)
    if incoming == zmq.POLLIN:
        teams = json.loads(socket.recv().decode('utf8'))
        if not teams:
            console.print("No teams found on the server :(")
            return None
        else:
            print("Server has the following teams available")
    else:
        console.print(f"Server did not reply in {WAIT_TIMEOUT} ms.")
        return None

    players = []
    for addr, team_name in teams.items():
        console.print(f"  [blue]{len(players)})[/] {team_name} \\[[blue]{addr}[/]]", highlight=False)
        players.append(addr)

    if players:
        console.print("  [blue]r)[/] Random team")
        console.print("  [blue]s)[/] Server default")
        console.print("  [blue]x)[/] Exit")
        console.print()
        console.print(f"Found {len(players)} player{'s' if len(players) != 1 else ''}.")

        choices = {str(i): player for i, player in enumerate(players)}

        answer = Prompt.ask("[bold]Select player to play against (r for random, s server’s choice, x to exit)",
                            choices=list(choices) + ["r", "s", "x"],
                            default="r")

        if answer == "r":
            console.print("Choosing random player.")
            return random.choice(players)
        if answer == "s":
            console.print("Letting the server choose.")
            return team_spec
        elif answer in choices.keys():
            console.print(f"Choosing [blue]{choices[answer]}[/]", highlight=False)
            return choices[answer]
        else:
            return None


def w_h_string(s):
    """Parse WxH strings and return a tuple.

    600x400 -> (600,400)
    """
    if s in pelita.game.MSIZE:
        return pelita.game.MSIZE[s]
    try:
        x_string, y_string = s.split('x')
        w_h = (int(x_string), int(y_string))
    except ValueError:
        msg = "%s is not a valid specification" %s
        raise argparse.ArgumentTypeError(msg) from None
    return w_h

def parse_food_string(s):
    try:
        trapped, total = [int(item) for item in s.split(':')]
    except ValueError:
        msg = "%s is not a valid food specification" %s
        raise argparse.ArgumentTypeError(msg) from None
    return trapped, total


def long_help(s):
    return s if '--long-help' in sys.argv else argparse.SUPPRESS

parser = argparse.ArgumentParser(description='Run a single pelita game',
                                 add_help=False,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
parser._positionals = parser.add_argument_group('Arguments')
parser.add_argument('team_specs', help='FILENAME1.py FILENAME2.py (see below)', nargs='*', default=None)

parser._optionals = parser.add_argument_group('Options')
help_opt = parser._optionals.add_mutually_exclusive_group()
help_opt.add_argument('--help', '-h', help='Show this help message and exit.',
                    action='store_const', const=True)
help_opt.add_argument('--long-help', help='Show all possible options and exit.',
                    action='store_const', const=True)

parser.add_argument('--version', help='Show the version number and exit.',
                    action='store_const', const=True)
parser.add_argument('--log', help='Print debugging log information to'
                    ' LOGFILE (default \'stderr\').',
                    metavar='LOGFILE', const='-', nargs='?')
parser.add_argument('--write-replay', help=long_help('Print game dumps to file (will be overwritten)'),
                    metavar='REPLAYFILE', const='pelita.dump', nargs='?')
parser.add_argument('--replay', help=long_help('Replay a dumped game'),
                    metavar='REPLAYFILE', dest='replayfile', const='pelita.dump', nargs='?')
parser.add_argument('--store-output', help=long_help('Write all player’s stdout/stderr to the given folder (must exist)'),
                    metavar='FOLDER')
parser.add_argument('--check-team', action="store_true",
                    help=long_help('Check that the team is valid (on first sight) and print its name.'))
parser.add_argument('--append-blue', type=str, metavar='INFO', default=None,
                    help=long_help('Append info about the blue team (such as group id).'))
parser.add_argument('--append-red', type=str, metavar='INFO', default=None,
                    help=long_help('Append info about the red team (such as group id).'))
parser.add_argument('--store-layout', help='Generate layout and store it in LAYOUTFILE',
                    metavar='LAYOUTFILE', dest='layoutfile')

game_settings = parser.add_argument_group('Game settings')
game_settings.add_argument('--rounds', type=int, default=300,
                           help='Maximum number of rounds to play.')
game_settings.add_argument('--seed', type=int, metavar='SEED', default=None,
                           help='Initialize the random number generator with SEED.')
game_settings.add_argument('--allow-camping', const=True, action='store_const',
                           help='Food does not age when in a bot’s shadow')
game_settings.add_argument('--food', type=parse_food_string, metavar="T:F", default=None,
                        help="Distribute F food pellets for each team, with T being the number "
                        "of food pellets that are \"trapped\" within tunnels and chambers. "
                        " If not set use maze size specific defaults.")

layout_opt = game_settings.add_mutually_exclusive_group()
layout_opt.add_argument('--layout', metavar='FILENAME', help='Use layout from FILENAME')
layout_opt.add_argument('--size', type=w_h_string, metavar="STRING", default='normal',
                        help="Pick a random maze layout of specified size."
                        " Possible sizes: 'small' (16x8), 'normal' (32x16), 'big' (64x32), 'WxH' where W and H are integers. Default: 'normal'")

timeout_opt = game_settings.add_mutually_exclusive_group()
timeout_opt.add_argument('--timeout', type=float, metavar="SEC",
                         dest='timeout_length', help=f'Time before timeout is triggered (default: {pelita.game.TIMEOUT_SECS} seconds).')
timeout_opt.add_argument('--no-timeout', const=pelita.game.MAX_TIMEOUT_SECS, action='store_const',
                         dest='timeout_length', help='Run game without timeouts.')
game_settings.add_argument('--initial-timeout', type=float,  metavar="SEC", default=pelita.game.INITIAL_TIMEOUT_SECS,
                           dest='initial_timeout_length', help=long_help('Timeout to load a team'))
game_settings.add_argument('--error-limit', type=int, default=5,
                           dest='error_limit', help='Error limit. Reaching this limit disqualifies a team (default: 5).')
parser.set_defaults(timeout_length=pelita.game.TIMEOUT_SECS)
game_settings.add_argument('--stop-at', dest='stop_at', type=int, metavar="N",
                           help='Stop before playing round N.')
game_settings.add_argument('--stop-after-kill', dest='stop_after_kill', action='store_true',
                           help='Stop when a bot has been killed.')

viewer_settings = parser.add_argument_group('Viewer settings')
viewer_settings.add_argument('--geometry', type=w_h_string, metavar='NxM',
                    help='Set initial size of the game window.')
viewer_settings.add_argument('--fullscreen', const=True, action='store_const',
                    help='Make the game window run fullscreen')
viewer_settings.add_argument('--fps', type=float, default=40,
                    help='Set (approximate) number of frames per second in a graphical viewer.')

viewer_opt = viewer_settings.add_mutually_exclusive_group()
viewer_opt.add_argument('--null', action='store_const', const='null',
                        dest='viewer', help='Use no viewer on stdout.')
viewer_opt.add_argument('--ascii', action='store_const', const='ascii',
                        dest='viewer', help=long_help('Use the ASCII viewer.'))
viewer_opt.add_argument('--progress', action='store_const', const='progress',
                        dest='viewer', help=long_help('Use the progress viewer.'))
viewer_opt.add_argument('--tk', action='store_const', const='tk',
                        dest='viewer', help='Use the tk viewer (default).')
parser.set_defaults(viewer='tk')

advanced_settings = parser.add_argument_group('Advanced settings')
advanced_settings.add_argument('--reply-to', type=str, metavar='URL', dest='reply_to',
                               help=long_help('Communicate the result of the game on this channel.'))
advanced_settings.add_argument('--publish', type=str, metavar='URL', dest='publish_to',
                               help=long_help('Publish the game to this zmq socket.'))
advanced_settings.add_argument('--controller', type=str, metavar='URL', default="tcp://127.0.0.1",
                               help=long_help('Channel for controlling the game.'))

parser.epilog = """\
Team Specification:
    A team consists of a path to a .py file or to a Python module
    that defines at least:

    * TEAM_NAME
        a string with the name of the team.

    * move(bot, state) -> next_position
        a function which given a bot and a state returns the next position for
        current bot and a state.

    Example file: my_stopping_bots.py

        TEAM_NAME = 'My stopping bots'

        def move(bot, state):
            return bot.position

    A game between two teams of stopping bots can then be played as

        pelita my_stopping_bots.py my_stopping_bots.py

    Demo players can be found at https://github.com/ASPP/pelita_template
"""


def main():
    args = parser.parse_args()
    if args.help or args.long_help:
        parser.print_help()
        sys.exit(0)

    if args.version:
        print("Pelita {}".format(pelita.__version__))
        sys.exit(0)

    if args.log:
        start_logging(args.log)

    if args.rounds < 1:
        raise ValueError(f"Must play at least one round (rounds={args.rounds}).")

    if args.check_team:
        if not args.team_specs:
            raise ValueError("No teams specified.")
        for team_spec in args.team_specs:
            try:
                team_name = check_team(team_spec, timeout=args.initial_timeout_length)
                print("NAME:", team_name)
            except pelita.network.RemotePlayerFailure as e:
                if e.error_type == 'ModuleNotFoundError':
                    #print(f"{e.message}")
                    pass
                else:
                    raise
        sys.exit(0)

    if args.viewer == 'null':
        viewers = []
    elif args.viewer == 'tk':
        geometry = args.geometry
        delay = int(1000./args.fps)
        stop_at = args.stop_at
        stop_after_kill = args.stop_after_kill

        viewer_options = {
            "fullscreen" : args.fullscreen,
            "geometry": geometry,
            "delay": delay,
            "stop_at": stop_at,
            "stop_after_kill": stop_after_kill
        }
        viewers = [('tk', viewer_options)]
    else:
        viewers = [(args.viewer, None)]

    if args.reply_to:
        viewers.append(('reply-to', args.reply_to))
    if args.publish_to:
        viewers.append(('publish-to', args.publish_to))
    if args.write_replay:
        viewers.append(('write-replay-to', args.write_replay))

    if args.replayfile:
        viewer_state = pelita.game.setup_viewers(viewers)
        if pelita.game.controller_await(viewer_state, await_action='set_initial'):
            sys.exit(0)

        old_game = Path(args.replayfile).read_text().split("\x04")
        for state in old_game:
            if not state.strip():
                continue
            state = json.loads(state)
            # walls, bots, food must be list of tuple
            state['walls'] = list(map(tuple, state['walls']))
            state['bots'] = list(map(tuple, state['bots']))
            state['food'] = list(map(tuple, state['food']))
            for viewer in viewer_state['viewers']:
                viewer.show_state(state)
            if pelita.game.controller_await(viewer_state):
                break

        sys.exit(0)

    # Run a normal game
    num_teams = 2
    team_specs = args.team_specs
    if len(team_specs) == 0:
        team_specs = ('0', '1')
    if len(team_specs) == 1:
        raise RuntimeError("Not enough teams given. Must be {}".format(num_teams))
    if len(team_specs) > num_teams:
        raise RuntimeError("Too many teams given. Must be < {}.".format(num_teams))

    for idx, team_spec in enumerate(team_specs):
        if team_spec == "SCAN":
            scanned_spec = scan(team_spec)
            if scanned_spec:
                team_specs[idx] = scanned_spec
            else:
                print("No remote team found. Exiting.")
                return
        elif team_spec.startswith("pelita://"):
            # check if we need to send a server scan request
            parsed_url = urlparse(team_spec)
            if parsed_url.path in ('', '/'):
                scanned_spec = scan_server(team_spec)
                if scanned_spec:
                    team_specs[idx] = scanned_spec
                else:
                    print("No remote team selected. Exiting.")
                    return

    if args.seed is None:
        seed = random.randint(0, sys.maxsize)
    else:
        seed = args.seed

    rng = random.Random(seed)

    if args.layout:
        # first check if the given layout is a file
        layout_path = Path(args.layout)
        if layout_path.exists():
            layout_string = layout_path.read_text()
            layout_dict = pelita.layout.parse_layout(layout_string)
        else:
            raise FileNotFoundError(f'Layout file "{layout_path}" does not exist.')
    else:
        width, height = args.size

        if args.food:
            trapped_food, total_food = args.food
        elif (width, height) in pelita.game.NFOOD:
            trapped_food, total_food = pelita.game.NFOOD[(width, height)]
        else:
            raise ValueError('--food option must be specified if a custom maze size is set')

        layout_dict = pelita.maze_generator.generate_maze(trapped_food=trapped_food,
                                                          total_food=total_food,
                                                          width=width,
                                                          height=height, rng=rng)

    if args.layoutfile:
        # We only want to print this, when no seed has been given.
        if args.seed is None and not args.layout:
            print(f"Regenerate this layout with --seed {seed}")
        if args.layoutfile == '-':
            print(pelita.layout.layout_as_str(**layout_dict))
        else:
            with open(args.layoutfile, 'wt') as layoutfile:
                layoutfile.write(pelita.layout.layout_as_str(**layout_dict))
        sys.exit(0)

    if args.seed is None:
        # We only want to print this, when no seed has been given.
        print(f"Replay this game with --seed {seed}")

    pelita.game.run_game(team_specs=team_specs, max_rounds=args.rounds, layout_dict=layout_dict, rng=rng,
                         allow_camping=args.allow_camping, timeout_length=args.timeout_length,
                         initial_timeout_length=args.initial_timeout_length, error_limit=args.error_limit,
                         viewers=viewers,
                         store_output=args.store_output,
                         team_infos=(args.append_blue, args.append_red))

if __name__ == '__main__':
    main()
