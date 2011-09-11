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
    try:
        player = getattr(pelita.player, name)
    except AttributeError:
        msg = 'Failed to find %s in pelita.player' % (name,)
        raise ImportError(msg)
    return player

def create_builtin_team(spec):
    names = spec.split(',')
    if len(names) == 1:
        names *= 2
    elif len(names) > 2:
        raise ValueError('need two comma seperated names')

    players = [import_builtin_player(name)() for name in names]
    return pelita.player.SimpleTeam(name + 's', *players)

def load_team(spec):
    if '/' in spec or spec.endswith('.py'):
        return load_factory(spec)()
    else:
        return create_builtin_team(spec)

parser = argparse.ArgumentParser('run a pelita game')
parser.add_argument('bad_team', help='team on the left side')
parser.add_argument('good_team', help='team on the right side')

def run_game(*argv):
    print "args: ", argv
    args = parser.parse_args(argv)
    bads = load_team(args.bad_team)
    goods = load_team(args.good_team)

    for team in (bads, goods):
        client = pelita.simplesetup.SimpleClient(team)
        client.autoplay_background()
    server = pelita.simplesetup.SimpleServer()
    server.run_tk()

if __name__ == '__main__':
    run_game(*sys.argv[1:])
