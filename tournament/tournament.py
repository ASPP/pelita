#!/usr/bin/env python3

import argparse
import builtins
import io
import itertools
import os
import random
import sys
import tempfile
import time
from subprocess import PIPE, STDOUT, Popen, check_call

import yaml

from tournament import tournament
from tournament.tournament import Config, State

# Tournament log file
DUMPSTORE = None

# Number of points a teams gets for matches in the first round
# Probably not worth it to make it options.
POINTS_DRAW = 1
POINTS_WIN = 2

SPEAK = True
LOGFILE = None

os.environ["PELITA_PATH"] = os.environ.get("PELITA_PATH") or os.path.join(os.path.dirname(sys.argv[0]), "..")

DEFAULT_PELITAGAME = os.path.join(os.path.dirname(sys.argv[0]), '../pelitagame')

def create_directory(prefix):
    for suffix in itertools.count(0):
        name = '{}-{:02d}'.format(prefix, suffix)
        try:
            os.mkdir(name)
        except FileExistsError:
            pass
        else:
            break
    return name


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run a tournament',
                                     add_help=False,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser._positionals = parser.add_argument_group('Arguments')
    parser.add_argument('pelitagame', help='The pelitagame script',
                        default=DEFAULT_PELITAGAME, nargs='?')
    parser._optionals = parser.add_argument_group('Options')
    parser.add_argument('--help', '-h',
                        help='show this help message and exit',
                        action='store_true')
    parser.add_argument('--speak', '-s',
                        help='speak loudly every messsage on stdout',
                        action='store_true')
    parser.add_argument('--speaker',
                        help='tool to say stuff',
                        type=str, default="/usr/bin/flite")
    parser.add_argument('--rounds', '-r',
                        help='maximum number of rounds to play per match',
                        type=int)
    parser.add_argument('--viewer', '-v',
                        type=str, help='the pelita viewer to use (default: tk)')
    parser.add_argument('--config', help='tournament data',
                        metavar="CONFIG_YAML", default="tournament.yaml")
    parser.add_argument('--interactive', help='ask before proceeding',
                        action='store_true', default=False)
    parser.add_argument('--state', help='store state',
                        metavar="STATEFILE", default='state.yaml')
    parser.add_argument('--load-state', help='load state from file',
                        action='store_true')
    parser.add_argument('--no-log', help='do not store the log data',
                        action='store_true')
    parser.add_argument('--dry-run', help='do not actually play',
                        action='store_true')

    global ARGS
    ARGS = parser.parse_args()
    if ARGS.help:
        parser.print_help()
        sys.exit(0)


    # Check that pelitagame can be run
    if not os.path.isfile(ARGS.pelitagame):
        sys.stderr.write(ARGS.pelitagame+' not found!\n')
        sys.exit(2)
    else:
        # Define the command line to run a pelita match
        CMD_STUB = [ARGS.pelitagame,
                    '--rounds=%d'%ARGS.rounds,
        #            '--%s'%ARGS.viewer]
        '--publish-to', 'tcp://127.0.0.1:51234'
                        ] # '%ARGS.viewer]

    if not ARGS.no_log:
        # create a directory for the dumps
        DUMPSTORE = create_directory('./dumpstore')

        # open the log file (fail if it exists)
        logfile = os.path.join(DUMPSTORE, 'log')
        fd = os.open(logfile, os.O_CREAT|os.O_EXCL|os.O_WRONLY, 0o0666)
        LOGFILE = os.fdopen(fd, 'w')

    with open(ARGS.config) as f:
        config_data = yaml.load(f)
        config_data['viewer'] = ARGS.viewer or config_data.get('viewer', 'tk')
        config_data['interactive'] = ARGS.interactive
        config_data['statefile'] = ARGS.state

        config = Config(config_data)

    if ARGS.rounds:
        config.rounds = ARGS.rounds

    # Check speaking support
    SPEAK = ARGS.speak and os.path.exists(ARGS.speaker)

    if os.path.isfile(ARGS.state):
        if not ARGS.load_state:
            config.print("Found state file in {state_file}. Restore with --load-state. Aborting.".format(state_file=ARGS.state))
            sys.exit(-1)
        else:
            state = State.load(config, ARGS.state)
    else:
        state = State(config)

    random.seed(config.seed)

    tournament.present_teams(config)

    rr_ranking = tournament.round1(config, state)
    state.round2["round_robin_ranking"] = rr_ranking
    state.save(ARGS.state)

    if config.bonusmatch:
        sorted_ranking = tournament.komode.sort_ranks(rr_ranking[:-1]) + [rr_ranking[-1]]
    else:
        sorted_ranking = tournament.komode.sort_ranks(rr_ranking)

    winner = tournament.round2(config, sorted_ranking, state)

    config.print('The winner of the %s Pelita tournament is...' % config.location, wait=2, end=" ")
    config.print('{team_name}. Congratulations'.format(team_name=config.team_name(winner)), wait=2)
    config.print('Good evening master. It was a pleasure to serve you.')
