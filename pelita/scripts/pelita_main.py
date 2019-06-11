#!/usr/bin/env python3

import argparse
import contextlib
import json
import logging
import os
from pathlib import Path
import random
import subprocess
import sys
import time

import pelita
from pelita import libpelita, game, layout

# silence stupid warnings from logging module
logging.root.manager.emittedNoHandlerWarning = 1
_logger = logging.getLogger(__name__)


def geometry_string(s):
    """Get a X-style geometry definition and return a tuple.

    600x400 -> (600,400)
    """
    try:
        x_string, y_string = s.split('x')
        geometry = (int(x_string), int(y_string))
    except ValueError:
        msg = "%s is not a valid geometry specification" %s
        raise argparse.ArgumentTypeError(msg)
    return geometry


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
parser.add_argument('--dump', help=long_help('Print game dumps to file (will be overwritten)'),
                    metavar='DUMPFILE', const='pelita.dump', nargs='?')
parser.add_argument('--replay', help=long_help('Replay a dumped game'),
                    metavar='DUMPFILE', dest='replayfile', const='pelita.dump', nargs='?')
parser.add_argument('--list-layouts', action='store_true',
                    help='List all available layouts.')
parser.add_argument('--check-team', action="store_true",
                    help=long_help('Check that the team is valid (on first sight) and print its name.'))

game_settings = parser.add_argument_group('Game settings')
game_settings.add_argument('--rounds', type=int, default=300,
                           help='Maximum number of rounds to play.')
game_settings.add_argument('--seed', type=int, metavar='SEED', default=None,
                           help='Initialize the random number generator with SEED.')

layout_opt = game_settings.add_mutually_exclusive_group()
layout_opt.add_argument('--layoutfile', metavar='FILE',
                        help='Load a maze layout from FILE.')
layout_opt.add_argument('--layout', metavar='NAME',
                        help='Load a maze layout by name.')
layout_opt.add_argument('--filter', metavar='STRING', default='normal_without_dead_ends',
                        help='Restrict the pool of random layouts to those whose name contains STRING.'
                        ' Default: \'normal_without_dead_ends\'')

timeout_opt = game_settings.add_mutually_exclusive_group()
timeout_opt.add_argument('--timeout', type=float, metavar="SEC",
                         dest='timeout_length', help='Time before timeout is triggered (default: 3 seconds).')
timeout_opt.add_argument('--no-timeout', const=None, action='store_const',
                         dest='timeout_length', help='Run game without timeouts.')
game_settings.add_argument('--max-timeouts', type=int, default=5,
                           dest='max_timeouts', help='Maximum number of timeouts allowed (default: 5).')
parser.set_defaults(timeout_length=3)
game_settings.add_argument('--stop-at', dest='stop_at', type=int, metavar="N",
                           help='Stop before playing round N.')

viewer_settings = parser.add_argument_group('Viewer settings')
viewer_settings.add_argument('--geometry', type=geometry_string, metavar='NxM',
                    help='Set initial size of the game window.')
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
viewer_opt.add_argument('--tk-no-sync', action='store_const', const='tk-no-sync',
                        dest='viewer', help=long_help('Uses the tk viewer in an unsynchronized mode.'))
parser.set_defaults(viewer='tk')
parser.add_argument('--export-svg', dest="export_svg", type=str, metavar='FOLDER',
                    help=long_help('Export svg to given folder.'))

advanced_settings = parser.add_argument_group('Advanced settings')
advanced_settings.add_argument('--reply-to', type=str, metavar='URL', dest='reply_to',
                               help=long_help('Communicate the result of the game on this channel.'))

publisher_opt = advanced_settings.add_mutually_exclusive_group()
publisher_opt.add_argument('--publish', type=str, metavar='URL', dest='publish_to',
                           help=long_help('Publish the game to this zmq socket.'))
publisher_opt.add_argument('--no-publish', const=False, action='store_const', dest='publish_to',
                           help=long_help('Do not publish.'))
parser.set_defaults(publish_to="tcp://127.0.0.1:*")

advanced_settings.add_argument('--controller', type=str, metavar='URL', default="tcp://127.0.0.1:*",
                               help=long_help('Channel for controlling the game.'))
advanced_settings.add_argument('--external-controller', const=True, action='store_const',
                               help=long_help('Force control by an external controller.'))

parser.epilog = """\
Team Specification:
    A team consists of a path to a .py file or to a Python module
    that defines at least:

    * TEAM_NAME
        a string with the name of the team.

    * move(turn, game) -> next_move
        a function that takes the current game and returns the move for the bot
        with index `turn`, where `turn` is 0 or 1.

    Example file: my_stopping_bots.py

        TEAM_NAME = 'My stopping bots'

        def move(turn, game):
            return (0, 0)

    A game between two teams of stopping bots can then be played as

        pelita my_stopping_bots.py my_stopping_bots.py

    Demo players can be found at https://github.com/ASPP/pelita_template

Layout specification:
    If neither --layoutfile nor --layout are specified, the maze is
    chosen at random from the pool of available layouts.
    You can restrict this pool by using --filter.
"""


def main():
    args = parser.parse_args()
    if args.help or args.long_help:
        parser.print_help()
        sys.exit(0)

    if args.version:
        git_version = pelita._git_version()
        if git_version:
            print("Pelita {} (git: {})".format(pelita.__version__, git_version))
        else:
            print("Pelita {}".format(pelita.__version__))
        sys.exit(0)

    if args.list_layouts:
        layouts = pelita.layout.get_available_layouts()
        print('\n'.join(layouts))
        sys.exit(0)

    if args.viewer.startswith('tk') and not args.publish_to:
        raise ValueError("Options --tk (or --tk-no-sync) and --no-publish are mutually exclusive.")

    if args.log:
        libpelita.start_logging(args.log)

    if args.check_team:
        if not args.team_specs:
            raise ValueError("No teams specified.")
        for team_spec in args.team_specs:
            team_name = libpelita.check_team(team_spec)
            print("NAME:", team_name)
        sys.exit(0)

    if args.viewer == 'null':
        viewers = []
    else:
        viewers = [args.viewer]

    if args.export_svg:
        viewers.append(('svg', args.export_svg))

    geometry = args.geometry
    delay = int(1000./args.fps)
    stop_at = args.stop_at

    viewer_options = {
        "geometry": geometry,
        "delay": delay,
        "stop_at": stop_at
    }

    if args.reply_to:
        viewers.append(('reply-to', args.reply_to))
    if args.dump:
        viewers.append(('dump-to', args.dump))
    
    if args.replayfile:
        viewer_state = game.setup_viewers(viewers, options=viewer_options)
        if game.controller_exit(viewer_state, await_action='set_initial'):
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
            if game.controller_exit(viewer_state):
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

    if args.seed is None:
        seed = random.randint(0, sys.maxsize)
        args.seed = seed
        print("Replay this game with --seed {seed}".format(seed=seed))
    else:
        pass
    random.seed(args.seed)

    if args.layout:
        layout_name = args.layout
        layout_string = pelita.layout.get_layout_by_name(args.layout)
    elif args.layoutfile:
        layout_path = Path(args.layoutfile)
        layout_name = str(layout_path)
        layout_string = layout_path.read_text()
    else:
        layout_name, layout_string = pelita.layout.get_random_layout(args.filter)

    print("Using layout '%s'" % layout_name)

    layout_dict = layout.parse_layout(layout_string)
    game.run_game(team_specs=team_specs, max_rounds=args.rounds, layout_dict=layout_dict, layout_name=layout_name, seed=args.seed,
                  timeout_length=args.timeout_length, max_team_errors=args.max_timeouts, dump=args.dump,
                  viewers=viewers, viewer_options=viewer_options)

if __name__ == '__main__':
    main()
