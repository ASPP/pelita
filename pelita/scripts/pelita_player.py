#!/usr/bin/env python3

import argparse
import inspect
import keyword
import os
import random
import string
import sys

import pelita

parser = argparse.ArgumentParser(description="Runs a Python pelita module.")
parser.add_argument('team')
parser.add_argument('address')

def make_client():
    args = parser.parse_args()

    team = load_team(args.team)
    print("Using factory '%s' -> '%s'" % (args.team, team.team_name))

    addr = args.address
    addr = addr.replace('*', 'localhost')
    client = pelita.simplesetup.SimpleClient(team, address=addr)
    return client

def check_module(filepath):
    "Throws an ValueError is the specified path is neither a module nor a package."
    if not os.path.exists(filepath):
        raise ValueError("'%s' doesn't exist" % filepath)
    allowed = string.ascii_letters + string.digits + '_'
    if filepath.endswith('.py'):
        valid = os.path.isfile(filepath)
        modname = os.path.basename(filepath[:-3])
    else:
        initpy = os.path.join(filepath, '__init__.py')
        valid = os.path.isdir(filepath) and os.path.isfile(initpy)
        modname = os.path.basename(filepath.rstrip(os.path.sep))
    if (set(modname) - set(allowed) or
        modname[0] in string.digits or
        modname in keyword.kwlist or
        modname.startswith('__')):
        raise ValueError("invalid module name: '%s'" % modname)

    if not valid:
        raise ValueError("'%s': neither a module nor a package" % filepath )

def create_builtin_team(spec):
    names = spec.split(',')
    if len(names) == 1:
        names *= 2
    elif len(names) > 2:
        raise ValueError('need two comma separated names')

    players = [import_builtin_player(name)() for name in names]
    teamname = 'The %ss' % players[0].__class__.__name__
    return pelita.player.SimpleTeam(teamname, *players)


def check_team_name(name):
    # Team name must be ascii
    try:
        name.encode('ascii')
    except UnicodeDecodeError:
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
    try:
        if '/' in spec or spec.endswith('.py') or os.path.exists(spec):
            team = load_factory(spec)()
        else:
            team = create_builtin_team(spec)
        check_team_name(team.team_name)
        return team
    except (ValueError, AttributeError, IOError, ImportError) as e:
        print("failure while loading team '%s'" % spec, file=sys.stderr)
        print('ERROR: %s' % e, file=sys.stderr)
        raise

def load_factory(filespec):
    filename, _, factory_name = filespec.partition(':')
    check_module(filename)
    filename = filename.rstrip(os.path.sep)
    dirname = os.path.dirname(filename)
    modname = os.path.splitext(os.path.basename(filename))[0]

    factory_name = factory_name or 'factory'
    with pelita.utils.with_sys_path(dirname):
        module = __import__(modname, fromlist=[factory_name])
    return getattr(module, factory_name)

def import_builtin_player(name):
    with pelita.utils.with_sys_path("./"):
        players_module = __import__('pelita.players', fromlist='players')
        sane_players = {p.__name__: p for p in players_module.SANE_PLAYERS}

    if name == 'random':
        player = random.choice(list(sane_players.values()))
        print('Choosing %s for random player' % player)
    else:
        player = sane_players.get(name)
        if not player:
            try:
                # fallback to player in pelita.player
                player = getattr(pelita.player, name)
            except AttributeError:
                others = ', '.join(list(sane_players.keys()))
                msg = 'Failed to find %s in players. (Available players are: %s).' % (name, others)
                raise ImportError(msg)

    if inspect.isclass(player) and issubclass(player, pelita.player.AbstractPlayer):
        return player
    else:
        raise ImportError("%r is not a valid player." % player)

def main():
    client = make_client()
    ret = client.run()
    sys.exit(ret)

if __name__ == '__main__':
    main()
