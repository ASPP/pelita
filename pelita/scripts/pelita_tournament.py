#!/usr/bin/env python3

import argparse
import datetime
import itertools
import logging
import os
import pathlib
import random
import re
import shlex
import sys

import shutil
import yaml

from .. import libpelita
from ..tournament import tournament
from ..tournament.tournament import Config, State


def start_logging(filename):
    if filename:
        hdlr = logging.FileHandler(filename, mode='w')
    else:
        hdlr = logging.StreamHandler()
    logger = logging.getLogger('pelita-tournament')
    FORMAT = '[%(relativeCreated)06d %(name)s:%(levelname).1s][%(funcName)s] %(message)s'
    formatter = logging.Formatter(FORMAT)
    hdlr.setFormatter(formatter)
    logger.addHandler(hdlr)
    logger.setLevel(logging.DEBUG)


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

def input_choice(text, choices, vars):
    selected = ""
    while not selected or selected not in vars:
        print(text)
        for choice in choices:
            print(choice)
        selected = input().strip()
    return selected


def autoconf_sound():
    res = {}
    which_say = shutil.which("say")
    if which_say:
        res["say"] = [which_say, "-f"]
    which_flite = shutil.which("flite")
    if which_flite:
        res["flite"] = [which_flite]
    return res


def setup():
    config = {}
    print("Where should the next tournament be?")
    config['location'] = input()
    print("When should the next tournament be? (ex. {year})".format(year=datetime.datetime.now().year))
    config['date'] = input()

    while True:
        sound = autoconf_sound()
        sound_options = [
            "(e)nter manually",
        ]
        keys = "e"

        try:
            which_say = sound["say"]
            sound_options.append("(s)ay ({})".format(sound["say"]))
            keys += "s"
        except KeyError:
            pass

        try:
            which_say = sound["flite"]
            sound_options.append("(f)flite ({})".format(sound["flite"]))
            keys += "f"
        except KeyError:
            pass

        sound_options.append("(n)o sound")
        keys += "n"
        sound_options.append("(r)etry search")
        keys += "r"

        res = input_choice("Enable sound?", sound_options, keys)
        if res == "n":
            config["speak"] = False
            break
        elif res == "e":
            print("Please enter the location of the sound-giving binary:")
            sound_path = input()
        elif res == "s":
            sound_path = libpelita.shlex_unsplit(sound["say"])
        elif res == "f":
            sound_path = libpelita.shlex_unsplit(sound["flite"])
        else:
            continue

        print("Now trying to speak:")
        config["speak"] = True
        config['speaker'] = sound_path
        # must set a few dummy variables
        config['teams'] = []
        config['bonusmatch'] = []
        Config(config).say("Hello my master.")
        success = input_choice("Did you hear any sound? (y/n)", [], "yn")
        if success == "y":
            del config["teams"]
            del config["bonusmatch"]
            break

    print("Specify the folder where we should look for teams (or none)")
    folder = input().strip()
    if folder:
        try:
            subfolders = [x.as_posix() for x in pathlib.Path(folder).iterdir() if x.is_dir()
                                                                               and not x.name.startswith('.')
                                                                               and not x.name.startswith('_')]
            config["teams"] = [{ 'spec': folder, 'members': []} for folder in subfolders]
        except FileNotFoundError:
            print("Invalid path: {}".format(folder))

    res = input_choice("Should a bonus match be played? (y/n/i)", [], "yni")
    if res == "y":
        config['bonusmatch'] = True
    elif res == "n":
        config['bonusmatch'] = False

    def escape(str):
        return "-" + re.sub(r'[\W]', '_', str) if str else ""

    file_name = "tournament{location}{year}.yaml".format(location=escape(config["location"]),
                                                         year=escape(config["date"]))

    print("Writing to: {file_name}".format(file_name=file_name))
    with open(file_name, "x") as f:
        yaml.dump(config, f, default_flow_style=False)


def main():
    parser = argparse.ArgumentParser(description='Run a tournament',
                                     add_help=False,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser._positionals = parser.add_argument_group('Arguments')
    parser._optionals = parser.add_argument_group('Options')
    parser.add_argument('--help', '-h',
                        help='show this help message and exit',
                        action='store_true')

    parser.add_argument('--speak', dest='speak', action='store_true', help='speak loudly every messsage on stdout')
    parser.add_argument('--no-speak', dest='speak', action='store_false', help='do not speak every messsage on stdout')
    parser.set_defaults(speak=None)

    parser.add_argument('--speaker', help='tool to say stuff', type=str)

    parser.add_argument('--rounds', '-r',
                        help='maximum number of rounds to play per match',
                        type=int)
    parser.add_argument('--viewer', '-v',
                        type=str, help='the pelita viewer to use (default: tk)')
    parser.add_argument('--config', help='tournament data',
                        metavar="CONFIG_YAML", default="tournament.yaml")

    parser.add_argument('--interactive', dest='interactive', action='store_true', help='do not ask before proceeding')
    parser.add_argument('--non-interactive', dest='interactive', action='store_false', help='do not ask before proceeding')
    parser.set_defaults(interactive=None)

    parser.add_argument('--setup', action='store_true')

    parser.add_argument('--state', help='store state',
                        metavar="STATEFILE", default='state.yaml')
    parser.add_argument('--load-state', help='load state from file',
                        action='store_true')
    parser.add_argument('--no-log', help='do not store the log data',
                        action='store_true')
    parser.add_argument('--dry-run', help='do not actually play',
                        action='store_true')

    args = parser.parse_args()
    if args.help:
        parser.print_help()
        sys.exit(0)
    elif args.setup:
        setup()
        sys.exit(0)

    try:
        with open(args.config) as f:
            config_data = yaml.load(f)
            config_data['viewer'] = args.viewer or config_data.get('viewer', 'tk')
            config_data['interactive'] = libpelita.firstNN(args.interactive, config_data.get('interactive'), True)
            config_data['statefile'] = args.state
            config_data['speak'] = libpelita.firstNN(args.speak, config_data.get('speak'))
            config_data['speaker'] = args.speaker or config_data.get('speaker')

            config = Config(config_data)
    except FileNotFoundError:
        print("‘{}’ not found. Create a new tournament with ‘--setup’.".format(args.config))
        sys.exit(1)

    if not args.no_log:
        # create a directory for the dumps
        def escape(s):
            return "-" + re.sub(r'[\W]', '_', str(s)) if s else ""

        storage_folder = create_directory('./store{location}{year}'.format(location=escape(config.location),
                                                                      year=escape(config.date)))

        config.tournament_log_folder = storage_folder

        # open the log file (fail if it exists)
        logfile = os.path.join(storage_folder, 'tournament.out')
        #fd = os.open(logfile, os.O_CREAT|os.O_EXCL|os.O_WRONLY, 0o0666)
        config.tournament_log_file = logfile #os.fdopen(fd, 'w')

        try:
            start_logging(os.path.join(storage_folder, 'tournament.log'))
        except AttributeError:
            pass

    if args.rounds:
        config.rounds = args.rounds

    if os.path.isfile(args.state):
        if not args.load_state:
            config.print("Found state file in {state_file}. Restore with --load-state. Aborting.".format(state_file=args.state))
            sys.exit(-1)
        else:
            state = State.load(config, args.state)
    else:
        state = State(config)

    random.seed(config.seed)

    if state.round1['played']:
        # We have already played one match. Do not speak the introduction.
        old_speak = config.speak
        config.speak = False
        tournament.present_teams(config)
        config.speak = old_speak
    else:
        tournament.present_teams(config)

    rr_ranking = tournament.round1(config, state)
    state.round2["round_robin_ranking"] = rr_ranking
    state.save(args.state)

    if config.bonusmatch:
        sorted_ranking = tournament.komode.sort_ranks(rr_ranking[:-1]) + [rr_ranking[-1]]
    else:
        sorted_ranking = tournament.komode.sort_ranks(rr_ranking)

    winner = tournament.round2(config, sorted_ranking, state)

    config.print('The winner of the %s Pelita tournament is...' % config.location, wait=2, end=" ")
    config.print('{team_name}. Congratulations'.format(team_name=config.team_name(winner)), wait=2)
    config.print('Good evening master. It was a pleasure to serve you.')

if __name__ == '__main__':
    main()
