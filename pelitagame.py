import sys
import os.path
import contextlib
import argparse

import pelita

@contextlib.contextmanager
def with_sys_path(dirname):
    sys.path.insert(0, dirname)
    try:
        yield
    finally:
        sys.path.remove(dirname)

def load_factory(filename):
    dirname = os.path.dirname(filename)
    modname = os.path.splitext(os.path.basename(filename))[0]

    with with_sys_path(dirname):
        try:
            module = __import__(modname, fromlist=['factory'])
        except ImportError as e:
            msg = 'Failed to find factory in module %s: %s' % (filename, e)
            raise ImportError(msg)

    return module.factory

def import_builtin_player(name):
    pelita_player = pelita.player
    try:
        player = getattr(pelita_player, name)
    except AttributeError:
        others = [n for n in dir(pelita_player) if n.endswith('Player')]
        others = ', '.join(others)
        msg = 'Failed to find %s in pelita.player [%s]' % (name, others)
        raise ImportError(msg)
    return player

def create_builtin_team(spec):
    names = spec.split(',')
    if len(names) == 1:
        names *= 2
    elif len(names) > 2:
        raise ValueError('need two comma seperated names')

    players = [import_builtin_player(name)() for name in names]
    return pelita.player.SimpleTeam(names[0] + 's', *players)

def load_team(spec):
    if '/' in spec or spec.endswith('.py'):
        return load_factory(spec)()
    else:
        return create_builtin_team(spec)

parser = argparse.ArgumentParser('run a pelita game')
parser.add_argument('bad_team', help='team on the left side')
parser.add_argument('good_team', help='team on the right side')
viewer_opt = parser.add_mutually_exclusive_group()
viewer_opt.add_argument('--ascii', action='store_const', const='ascii',
                        dest='viewer', help='use the ASCII viewer')
viewer_opt.add_argument('--tk', action='store_const', const='tk',
                        dest='viewer', help='use the tk viewer (default)')
parser.set_defaults(viewer='tk')
layout_opt = parser.add_mutually_exclusive_group()
layout_opt.add_argument('--layoutfile', '-L', metavar='filename')
layout_opt.add_argument('--layout', '-l', metavar='name')
parser.add_argument('--rounds', '-r', type=int, default=3000)

def run_game(*argv):
    args = parser.parse_args(argv)

    if args.layout == 'list':
        layouts = pelita.layout.get_available_layouts()
        print '\n'.join(layouts)
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

    print args
    if args.viewer in 'tk':
        server.run_tk()
    elif args.viewer == 'ascii':
        server.run_ascii()
    else:
        assert 0

if __name__ == '__main__':
    run_game(*sys.argv[1:])
