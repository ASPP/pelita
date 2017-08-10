#!/usr/bin/env python3

import argparse
import contextlib
import json
import logging
import os
import random
import subprocess
import sys
import time

import pelita
from pelita import libpelita

# silence stupid warnings from logging module
logging.root.manager.emittedNoHandlerWarning = 1
_logger = logging.getLogger("pelitagame")

class ReplayPublisher:
    def __init__(self, publish_sock, replayfile):
        with open(replayfile) as f:
            self.old_game = f.read().split("\x04")

        self.publisher = pelita.simplesetup.SimplePublisher(publish_sock)

    def run(self):
        for state in self.old_game:
            if state:
                message = json.loads(state)
                self.publisher._send(message)

class ResultPrinter(pelita.viewer.AbstractViewer):
    def observe(self, universe, game_state):
        self.print_bad_bot_status(universe, game_state)
        if game_state["finished"]:
            self.print_possible_winner(universe, game_state)

    def print_bad_bot_status(self, universe, game_state):
        for bot_id, reason in game_state["bot_error"].items():
            if reason == "timeout":
                sys.stderr.write("Timeout #%r for team %r (bot index %r).\n" % (
                                  game_state["timeout_teams"][universe.bots[bot_id].team_index],
                                  universe.bots[bot_id].team_index,
                                  bot_id))

            else:
                sys.stderr.write("Problem for team %r (bot index %r) (%s).\n" % (
                                  universe.bots[bot_id].team_index,
                                  bot_id,
                                  reason))

        for team_id, reason in enumerate(game_state["teams_disqualified"]):
            if reason == "timeout":
                sys.stderr.write("Team %r had too many timeouts. Team disqualified.\n" % team_id)
            elif reason == "disconnected":
                sys.stderr.write("Team %r disconnected. Team disqualified.\n" % team_id)
            elif reason is not None:
                sys.stderr.write("Team %r disqualified (%r).\n" % (team_id, reason))


    def print_possible_winner(self, universe, game_state):
        """ Checks the event list for a potential winner and prints this information.

        This is needed for pelita.scripts parsing the output.
        """
        winning_team = game_state.get("team_wins")
        if winning_team is not None:
            winner = universe.teams[winning_team]
            winner_name = game_state["team_name"][winner.index]
            loser = universe.enemy_team(winning_team)
            loser_name = game_state["team_name"][loser.index]
            msg = "Finished. '%s' won over '%s'. (%r:%r)" % (
                    winner_name, loser_name,
                    winner.score, loser.score
                )
            sys.stdout.flush()
        elif game_state.get("game_draw") is not None:
            t0 = universe.teams[0]
            t0_name = game_state["team_name"][t0.index]
            t1 = universe.teams[1]
            t1_name = game_state["team_name"][t1.index]
            msg = "Finished. '%s' and '%s' had a draw. (%r:%r)" % (
                    t0_name, t1_name,
                    t0.score, t1.score
                )
        else:
            return

        print(msg)
        # We must manually flush, else our forceful stopping of Tk
        # won't let us pipe it.
        sys.stdout.flush()

def default_players():
    from ..players import SANE_PLAYERS
    return sorted(SANE_PLAYERS, key=lambda m: m.__name__)

def start_logging(filename):
    if filename:
        hdlr = logging.FileHandler(filename, mode='w')
    else:
        hdlr = logging.StreamHandler()
    logger = logging.getLogger('pelita')
    FORMAT = \
    '[%(relativeCreated)06d %(name)s:%(levelname).1s][%(funcName)s] %(message)s'
    formatter = logging.Formatter(FORMAT)
    hdlr.setFormatter(formatter)
    logger.addHandler(hdlr)
    logger.setLevel(logging.DEBUG)

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

parser = argparse.ArgumentParser(description='Run a single pelita game',
                                 add_help=False,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
parser._positionals = parser.add_argument_group('Arguments')
parser.add_argument('team_specs', help='teams (default: random)', nargs='*', default=None)

parser._optionals = parser.add_argument_group('Options')
parser.add_argument('--help', '-h', help='show this help message and exit',
                    action='store_const', const=True)
parser.add_argument('--version', help='show the version number and exit',
                    action='store_const', const=True)
parser.add_argument('--log', help='print debugging log information to'
                                  ' LOGFILE (default \'stderr\')',
                    metavar='LOGFILE', default=argparse.SUPPRESS, nargs='?')
parser.add_argument('--dump', help='print game dumps to file (will be overwritten)'
                                  ' DUMPFILE (default \'pelita.dump\')',
                    metavar='DUMPFILE', default=argparse.SUPPRESS, nargs='?')
parser.add_argument('--replay', help='replay a dumped game'
                                  ' DUMPFILE (default \'pelita.dump\')',
                    metavar='DUMPFILE', default=argparse.SUPPRESS, nargs='?')
parser.add_argument('--rounds', type=int, default=300,
                    help='maximum number of rounds to play')
parser.add_argument('--fps', type=float, default=40,
                    help='(approximate) number of frames per second in a graphical viewer')
parser.add_argument('--seed', type=int, metavar='SEED', default=None,
                    help='fix random seed')
parser.add_argument('--geometry', type=geometry_string, metavar='NxM',
                    help='initial size of the game window')
parser.add_argument('--dry-run', const=True, action='store_const',
                    help='load players but do not actually play the game')
parser.add_argument('--max-timeouts', type=int, default=5,
                    dest='max_timeouts', help='maximum number of timeouts allowed (default: 5)')
parser.add_argument('--list-teams', action="store_const", const=True,
                    help='Print the names of the included default teams.')
parser.add_argument('--check-team', action="store_const", const=True,
                    help='Check that the team is valid (on first sight) and print its name.')

timeout_opt = parser.add_mutually_exclusive_group()
timeout_opt.add_argument('--timeout', type=float, metavar="SEC",
                         dest='timeout_length', help='time before timeout is triggered (default: 3 seconds)')
timeout_opt.add_argument('--no-timeout', const=None, action='store_const',
                         dest='timeout_length', help='run game with no timeouts')
parser.set_defaults(timeout_length=3)

parser.add_argument('--reply-to', type=str, metavar='URL',
                    dest='reply_to', help='Reply channel')

publisher_opt = parser.add_mutually_exclusive_group()
publisher_opt.add_argument('--publish', type=str, metavar='URL',
                           dest='publish_to', help='publish to this zmq socket')
publisher_opt.add_argument('--no-publish', const=False, action='store_const',
                           dest='publish_to', help='do not publish')
parser.set_defaults(publish_to="tcp://127.0.0.1:*")

controller_opt = parser.add_argument_group("Controller")
controller_opt.add_argument('--controller', type=str, metavar='URL', default="tcp://127.0.0.1:*",
                            help='open a controller on this zmq socket')
controller_opt.add_argument('--external-controller', const=True, action='store_const',
                            help='force control by an external controller')

viewer_opt = parser.add_mutually_exclusive_group()
viewer_opt.add_argument('--ascii', action='store_const', const='ascii',
                        dest='viewer', help='use the ASCII viewer')
viewer_opt.add_argument('--null', action='store_const', const='null',
                        dest='viewer', help='use the /dev/null viewer')
viewer_opt.add_argument('--progress', action='store_const', const='progress',
                        dest='viewer', help='use the progress viewer')
viewer_opt.add_argument('--tk', action='store_const', const='tk',
                        dest='viewer', help='use the tk viewer (default)')
viewer_opt.add_argument('--tk-no-sync', action='store_const', const='tk-no-sync',
                        dest='viewer', help='use the unsynchronised tk viewer')
parser.set_defaults(viewer='tk')

layout_opt = parser.add_mutually_exclusive_group()
layout_opt.add_argument('--layoutfile', metavar='FILE',
                        help='load a maze layout from FILE')
layout_opt.add_argument('--layout', metavar='NAME',
                        help="load a maze layout by name. If NAME is"
                        " 'list' return a list of available names")
layout_opt.add_argument('--filter', metavar='STRING',
                        default='normal_without_dead_ends',
                        help='retrict the pool of random layouts to those whose'
                        ' name contains STRING.'
                        ' Default: \'normal_without_dead_ends\'')

parser.epilog = """\
Team Specification:
  - Using predefined players:
    A single name (e.g. 'NQRandomPlayer') in which case the team is
    composed of players of this type, or a comma separated list of
    player types (e.g. 'BFSPlayer,BasicDefensePlayer'). Example usage:

        $ %(prog)s BFSPlayer,RandomPlayer NQRandomPlayer,BasicDefensePlayer

    Use --list-teams to get a list of predefined players.

  - Using custom players (filename):
    The name of a python file (e.g. '~/my_player.py') which defines
    a function named 'factory' (you can change the name of the factory
    function by adding ':my_factory' to the filename). The factory
    function must take no arguments and return an instance of
    pelita.player.SimpleTeam.
    Example implementation:

    def factory():
        return pelita.player.SimpleTeam("My Team", MyPlayer1(), MyPlayer2())

    Example usage:

        $ %(prog)s ~/my_player.py NQRandomPlayer,BasicDefensePlayer

    Example of custom factory function:

        $ %(prog)s ~/my_player.py:my_factory NQRandomPlayer,BasicDefensePlayer

  - Using custom players (package):
    The name of a python package (i.e. a directory with an __init__.py file),
    which exposes a function named 'factory' (see above for more details).
    Example usage:

        $ %(prog)s my_player NQRandomPlayer,BasicDefensePlayer

  - Using a different Python version:
    Additionally, player specifications may use a prefix (ending with @)
    to use a different executable for the subprocess.

        $ %(prog)s py3@my_new_player py2@my_old_player

    runs the first player with Python 3 and the second player with Python 2.
    A non-existing prefix is taken as ‘py@’ that is the very same Python version
    the pelitagame script is run with.

  - Using custom players (simpleclient):
    The address the server should bind on and wait for a client
    to connect to.

    Example of a server binding the left team to 'tcp://*:9005' and
    the right team to 'ipc:///tmp/mysocket':

        $ %(prog)s tcp://*:9005 ipc:///tmp/mysocket

    Example of a server binding the left team to 'tcp://*:9005' and
    using a built-in Player as the right team:

        $ %(prog)s tcp://*:9005 NQRandomPlayer,BasicDefensePlayer

Layout specification:
  If neither --layoutfile nor --layout are specified, the maze is
  chosen at random from the pool of available layouts.
  You can restrict this pool by using --filter.
"""


def main():
    config = {
        "publish-addr": None,
        "controller-addr": None,
        "viewers": [],
        "external-viewers": []
    }

    args = parser.parse_args()
    if args.help:
        parser.print_help()
        sys.exit(0)
    if args.version:
        if pelita._git_version:
            print("Pelita {} (git: {})".format(pelita.__version__, pelita._git_version))
        else:
            print("Pelita {}".format(pelita.__version__))
            
        sys.exit(0)
    if args.layout == 'list':
        layouts = pelita.layout.get_available_layouts()
        print('\n'.join(layouts))
        sys.exit(0)

    if args.list_teams:
        for player in default_players():
            print(player.__name__)
        sys.exit(0)

    if args.seed is None:
        seed = random.randint(0, sys.maxsize)
        args.seed = seed
        print("Replay this game with --seed {seed}".format(seed=seed))
    else:
        pass
    random.seed(args.seed)

    if args.viewer.startswith('tk') and not args.publish_to:
        raise ValueError("Options --tk (or --tk-no-sync) and --no-publish are mutually exclusive.")

    try:
        start_logging(args.log)
    except AttributeError:
        pass

    if args.check_team:
        if not args.team_specs:
            raise ValueError("No teams specified.")
        for team_spec in args.team_specs:
            team_name = libpelita.check_team(libpelita.prepare_team(team_spec))
            print("NAME:", team_name)
        sys.exit(0)

    try:
        # TODO: Re-include the dump.
        dump = args.dump or 'pelita.dump'
    except AttributeError:
        dump = None

    try:
        replayfile = args.replay or 'pelita.dump'
    except AttributeError:
        replayfile = None

    if replayfile:
        replay_publisher = ReplayPublisher(args.publish_to, replayfile)
        config["publish-addr"] = replay_publisher.publisher.socket_addr
        subscribe_sock = replay_publisher.publisher.socket_addr.replace('*', 'localhost')

        if args.viewer.startswith("tk"):
            args.viewer = "tk-no-sync"
        runner = replay_publisher.run
    else:
        if args.layout or args.layoutfile:
            layout_name, layout_string = pelita.layout.load_layout(layout_name=args.layout, layout_file=args.layoutfile)
        else:
            layout_name, layout_string = pelita.layout.get_random_layout(args.filter)
        print("Using layout '%s'" % layout_name)

        num_teams = 2
        team_specs = args.team_specs
        while len(team_specs) < num_teams:
            team_specs.append("random")
        if len(team_specs) > num_teams:
            raise RuntimeError("Too many teams given. Must be < {}.".format(num_teams))

        if args.dry_run:
            sys.exit(0)

        if args.viewer == 'tk-no-sync':
            # only use delay when not synced.
            initial_delay = 0.5
        else:
            initial_delay = 0.0

        game_config = {
            "rounds": args.rounds,
            "initial_delay": initial_delay,
            "max_timeouts": args.max_timeouts,
            "timeout_length": args.timeout_length,
            "layout_name": layout_name,
            "layout_string": layout_string,
            "seed": args.seed,
        }

        viewers = []
        if dump:
            viewers.append(pelita.viewer.DumpingViewer(open(dump, "w")))
        if args.viewer == 'ascii':
            viewers.append(pelita.viewer.AsciiViewer())
        if args.viewer == 'progress':
            viewers.append(pelita.viewer.ProgressViewer())
        if args.reply_to:
            viewers.append(pelita.viewer.ReplyToViewer(args.reply_to))
        if args.viewer == 'null':
            pass

        # Adding the result printer to the viewers.
        viewers.append(ResultPrinter())

        with libpelita.channel_setup(publish_to=args.publish_to) as channels:
            if args.viewer.startswith('tk'):
                geometry = args.geometry
                delay = int(1000./args.fps)
                controller = channels["controller"]
                publisher = channels["publisher"]
                game_config["publisher"] = publisher
                viewer = libpelita.run_external_viewer(publisher.socket_addr, controller.socket_addr, geometry=geometry, delay=delay)
                libpelita.run_game(team_specs=team_specs, game_config=game_config, viewers=viewers, controller=controller)
            else:
                libpelita.run_game(team_specs=team_specs, game_config=game_config, viewers=viewers)


if __name__ == '__main__':
    main()

