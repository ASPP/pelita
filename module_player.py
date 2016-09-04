#!/usr/bin/env python3

import argparse
import inspect
import keyword
import os
import random
import re
import string
import sys

import pelita

parser = argparse.ArgumentParser(description="Runs a Python pelita module.")
parser.add_argument('team')
parser.add_argument('address')


INIT_PY = '''\
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pelita.player import SimpleTeam

{player_imports}


# The default factory method, which this module must export.
# It must return an instance of `SimpleTeam`  containing
# the name of the team and the respective instances for
# the first and second player.

def factory():
    return SimpleTeam({team_name}, {player_instances})

# For testing purposes, one may use alternate factory methods::
#
#def testfactory():
#    return SimpleTeam("NiceTeam", OurFoodEater(), OurHunter())

'''


PLAYER_CLASS_PY = '''
# -*- coding: utf-8 -*-

from pelita.player import AbstractPlayer
from pelita.datamodel import stop

# use relative imports for things inside your module
from .utils import utility_function

class {player_class}(AbstractPlayer):
    """ Basically a clone of the RandomPlayer. """

    def __init__(self):
        # Do some basic initialisation here. You may also accept additional
        # parameters which you can specify in your factory.
        # Note that any other game variables have not been set yet. So there is
        # no ``self.current_uni`` or ``self.current_state``
        self.sleep_rounds = 0

    def set_initial(self):
        # Now ``self.current_uni`` and ``self.current_state`` are known.
        # ``set_initial`` is always called before ``get_move``, so we can do some
        # additional initialisation here

        # Just printing the universe to give you an idea, please remove all
        # print statements in the final player.
        print(self.current_uni.pretty)

    def check_pause(self):
        # make a pause every fourth step because whatever :)
        if self.sleep_rounds <= 0:
            if self.rnd.random() > 0.75:
                self.sleep_rounds = 3

        if self.sleep_rounds > 0:
            self.sleep_rounds -= 1
            texts = ["What a headache!", "#aspp2015", "Python School Munich"]
            self.say(self.rnd.choice(texts))
            return stop

    def get_move(self):
        utility_function()

        self.check_pause()

        # legal_moves returns a dict {{move: position}}
        # we always need to return a move
        possible_moves = list(self.legal_moves.keys())
        # selecting one of the moves
        return self.rnd.choice(possible_moves)

'''


UTILS_INIT_PY = '''
# -*- coding: utf-8 -*-

# This module would be a good place to put utility functions and classes.
# You don’t need to use this module but it may be a good idea to structurise
# your projects from the beginning.

# using a relative import to export this function
from .helper import utility_function

'''


UTILS_HELPER_PY = '''
# -*- coding: utf-8 -*-

def utility_function():
    pass
'''


def generate_team(path, team_name, *players):
    if os.listdir(path):
        raise RuntimeError("Cannot create team here. Directory {cwd} not empty".format(cwd=os.getcwd()))

    def sanitize(cls):
        return cls

    def to_lower(name):
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

    files_classes = {
        to_lower(player): sanitize(player) for player in players
    }

    player_imports = "\n".join('from .{file} import {cls}'.format(file=file_name, cls=class_name)
                               for file_name, class_name in files_classes.items())

    player_instances = {"{cls}()".format(cls=player_class) for player_class in files_classes.values()}

    init_py = INIT_PY.format(team_name=repr(team_name),
                             player_instances=', '.join(player_instances),
                             player_imports=player_imports)

    os.makedirs('team')
    with open(os.path.join('team', '__init__.py'), 'w') as f:
        f.write(init_py)
    for file_name, class_name in files_classes.items():
        with open(os.path.join('team', '{file}.py'.format(file=file_name)), 'w') as f:
            player_class_py = PLAYER_CLASS_PY.format(player_class=class_name)
            f.write(player_class_py)
    team_utils = os.path.join('team', 'utils')
    os.makedirs(team_utils)
    with open(os.path.join(team_utils, '__init__.py'), 'w') as f:
        f.write(UTILS_INIT_PY)
    with open(os.path.join(team_utils, 'helper.py'), 'w') as f:
        f.write(UTILS_HELPER_PY)
    os.makedirs('test')


def make_client(args):

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
        players_module = __import__("players")
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

if __name__ == '__main__':
    try:
        if sys.argv[1] == '--gen-team':
            generate_team('.', sys.argv[2], *sys.argv[3:])
            sys.exit()
    except IndexError:
        pass

    args = parser.parse_args()

    client = make_client(args)
    ret = client.run()
    sys.exit(ret)

