#!/usr/bin/env python
import sys
import os.path
import contextlib
import random


@contextlib.contextmanager
def with_sys_path(dirname):
    sys.path.insert(0, dirname)
    try:
        yield
    finally:
        sys.path.remove(dirname)

try:
    import argparse
except ImportError:
    from pelita.compat import argparse

import pelita
# start logging
import logging
hdlr = logging.FileHandler('pelita.log', mode='w')
logger = logging.getLogger('pelita')
FORMAT = '[%(asctime)s,%(msecs)03d][%(name)s:%(levelname)s][%(funcName)s] %(message)s'
formatter = logging.Formatter(FORMAT)
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)


def load_factory(filename):
    filename = filename.rstrip(os.path.sep)
    dirname = os.path.dirname(filename)
    modname = os.path.splitext(os.path.basename(filename))[0]

    with with_sys_path(dirname):
        module = __import__(modname, fromlist=['factory'])
    return module.factory

PLAYERS = [name for name in dir(pelita.player)
           if name.endswith('Player') and
              name not in ('AbstractPlayer', 'TestPlayer',
                           'StoppingPlayer', 'IOBoundPlayer',
                           'CPUBoundPlayer', 'MoveExceptionPlayer',
                           'InitialExceptionPlayer')]

def import_builtin_player(name):
    if name == 'random':
        name = random.choice(PLAYERS)
        print 'using %s for random player' % name
    try:
        player = getattr(pelita.player, name)
    except AttributeError:
        others = ', '.join(PLAYERS)
        msg = 'Failed to find %s in pelita.player [%s]' % (name, others)
        raise ImportError(msg)
    return player

def create_builtin_team(spec):
    names = spec.split(',')
    if len(names) == 1:
        names *= 2
    elif len(names) > 2:
        raise ValueError('need two comma separated names')

    players = [import_builtin_player(name)() for name in names]
    teamname = 'The %ss' % players[0].__class__.__name__
    return pelita.player.SimpleTeam(teamname, *players)

def load_team(spec):
    if '/' in spec or spec.endswith('.py'):
        return load_factory(spec)()
    else:
        return create_builtin_team(spec)

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

parser = argparse.ArgumentParser(description='Runs a single pelita game')
parser.add_argument('bad_team', help='team on the left side', nargs='?',
                    default="random")
parser.add_argument('good_team', help='team on the right side', nargs='?',
                    default="random")
viewer_opt = parser.add_mutually_exclusive_group()
viewer_opt.add_argument('--ascii', action='store_const', const='ascii',
                        dest='viewer', help='use the ASCII viewer')
viewer_opt.add_argument('--null', action='store_const', const='null',
                        dest='viewer', help='use the /dev/null viewer')
viewer_opt.add_argument('--tk', action='store_const', const='tk',
                        dest='viewer', help='use the tk viewer (default)')
parser.set_defaults(viewer='tk')
layout_opt = parser.add_mutually_exclusive_group()
layout_opt.add_argument('--layoutfile', '-L', metavar='filename')
layout_opt.add_argument('--layout', '-l', metavar='name')
parser.epilog = """\
A team is specified by a comma separated list of players. For example:
NQRandomPlayer,BFSPlayer.

If you don't specify one or both teams, you'll get random players.
Use 'list' as a team to get a list of predefined players.
Run '%(prog)s --layout list' to list layouts.
"""
parser.add_argument('--rounds', '-r', type=int, default=3000)
parser.add_argument('--geometry', type=geometry_string, metavar='NxM',
                    help='initial size of the game window')

def run_game(*argv):
    args = parser.parse_args(argv)

    if args.layout == 'list':
        layouts = pelita.layout.get_available_layouts()
        print '\n'.join(layouts)
        sys.exit(0)

    if 'list' in (args.bad_team, args.good_team):
        print '\n'.join(PLAYERS)
        sys.exit(0)

    bads = load_team(args.bad_team)
    goods = load_team(args.good_team)

    for team in (bads, goods):
        client = pelita.simplesetup.SimpleClient(team)
        client.autoplay_background()
    server = pelita.simplesetup.SimpleServer(layout_file=args.layoutfile,
                                             layout_name=args.layout,
                                             rounds=args.rounds,
                                             )

    if args.viewer in 'tk':
        server.run_tk(geometry=args.geometry)
    elif args.viewer == 'ascii':
        server.run_simple(pelita.viewer.AsciiViewer)
    elif args.viewer == 'null':
        server.run_simple(pelita.viewer.DevNullViewer)
    else:
        assert 0

if __name__ == '__main__':
    run_game(*sys.argv[1:])
