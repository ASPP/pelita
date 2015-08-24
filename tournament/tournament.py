#!/usr/bin/python3
# -*- coding:utf-8 -*-

import argparse
import builtins
import io
import itertools
import json
import os
import random
import sys
import tempfile
import time
from subprocess import PIPE, STDOUT, Popen, check_call

import yaml

from pelita import libpelita
import roundrobin
import komode

# Speaking external program.
# Probably not worth it to make it an option.
FLITE = '/usr/bin/flite'


# Tournament log file
DUMPSTORE = None

# Number of points a teams gets for matches in the first round
# Probably not worth it to make it options.
POINTS_DRAW = 1
POINTS_WIN = 2

SPEAK = True
LOGFILE = None

os.environ["PELITA_PATH"] = os.path.join(os.path.dirname(sys.argv[0]), "..")

class Config:
    def __init__(self, config):
        self.teams = {}

        teams = config["teams"]
        team_prefix = config["team_prefix"]
        # load team names
        for idx, team in enumerate(teams):
            team_id = team.get("id") or "{team_prefix}{id}".format(team_prefix=team_prefix, id=idx)
            team_spec = team["spec"]
            team_name = set_name(team_spec)
            self.teams[team_id] = {
                "spec": team_spec,
                "name": team_name,
                "members": team["members"]
            }

        self.location = config["location"]

        #: Global random seed.
        #: Keep it fixed or it may be impossible to replicate a tournament.
        #: Individual matches will get a random seed derived from this.
        self.seed = config.get("seed", 42)

        self.bonusmatch = config["bonusmatch"]

    @property
    def team_ids(self):
        return self.teams.keys()

    def team_name(self, team):
        return self.teams[team]["name"]

    def team_spec(self, team):
        return self.teams[team]["spec"]

class State:
    pass

def _print(*args, **kwargs):
    builtins.print(*args, **kwargs)
    if LOGFILE:
        kwargs['file'] = LOGFILE
        builtins.print(*args, **kwargs)

def print(*args, **kwargs):
    """Speak while you print. To disable set speak=False.
    You need the program %s to be able to speak.
    Set wait=X to wait X seconds after speaking."""%FLITE
    if len(args) == 0:
        _print()
        return
    stream = io.StringIO()
    wait = kwargs.pop('wait', 0.5)
    want_speak = kwargs.pop('speak', SPEAK)
    if not want_speak:
        _print(*args, **kwargs)
    else:
        _print(*args, file=stream, **kwargs)
        string = stream.getvalue()
        _print(string, end='')
        sys.stdout.flush()
        with tempfile.NamedTemporaryFile('wt') as text:
            text.write(string+'\n')
            text.flush()
            festival = check_call(FLITE.split()+[text.name])
        #time.sleep(wait)


def wait_for_keypress():
    if ARGS.interactive:
        input('---\n')

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

def present_teams(config):
    print('Hello master, I am the Python drone. I am here to serve you.', wait=1.5)
    print('Welcome to the %s Pelita tournament' % config.location, wait=1.5)
    print('This evening the teams are:', wait=1.5)
    for team_id, team in config.teams.items():
        print("{team_id}: {team_name}".format(team_id=team_id, team_name=team["name"]))
        for member in team["members"]:
            print("{member}".format(member=member), wait=0.1)
        # time.sleep(1)
        print()
    print('These were the teams. Now you ready for the fight?')


def set_name(team):
    """Get name of team."""

    try:
        team = libpelita.prepare_team(team)
        return libpelita.check_team(team)
    except Exception:
        print("*** ERROR: I could not load team", team, ". Please help!", speak=False)
        print(sys.stderr, speak=False)
        raise


def start_match(config, team1, team2):
    """Start a match between team1 and team2. Return which team won (1 or 2) or
    0 if there was a draw.
    """
    print()
    print('Starting match: '+ config.team_name(team1)+' vs ' + config.team_name(team2))
    print()
    wait_for_keypress()
    cmd = CMD_STUB + [config.team_spec(team1), config.team_spec(team2),
                       '--seed', str(random.randint(0, sys.maxsize))]
    global ARGS
    if not ARGS.no_log:
        dumpfile = os.path.join(DUMPSTORE, time.strftime('%Y%m%d-%H%M%S'))
        cmd += ['--dump', dumpfile]

    if ARGS.dry_run:
        print("Would run: {cmd}".format(cmd=cmd))
        print("Choosing winner at random.")
        return random.choice([0, 1, 2])

    stdout, stderr = Popen(cmd, stdout=PIPE, stderr=PIPE,
                           universal_newlines=True).communicate()
    tmp = reversed(stdout.splitlines())
    for lastline in tmp:
        if lastline.startswith('Finished.'):
            break
    else:
        print("*** ERROR: Apparently the game crashed. At least I could not find the outcome of the game.")
        print("*** Maybe stderr helps you to debug the problem")
        print(stderr, speak=False)
        print("***", speak=False)
        return 0
    if stderr:
        print("***", stderr, speak=False)
    print('***', lastline)
    if 'had a draw.' in lastline:
        return 0
    else:
        tmp = lastline.split("'")
        winner = tmp[1]
        loser = tmp[3]
        if winner == config.team_name(team1):
            print(config.team_name(team1), 'wins.')
            return 1
        elif winner == config.team_name(team2):
            print(config.team_name(team2), 'wins.')
            return 2
        else:
            print("Unable to parse winning result :(")
            return 0


def start_deathmatch(config, team1, team2):
    """Start a match between team1 and team2 until one of them wins (ie no
    draw.)
    """
    print()
    print()
    print("{} v {}".format(team1, team2))
    for i in range(3):
        r = start_match(config, team1, team2)
        if r == 0:
            print('Draw -> Now go for a Death Match!')
            continue
        winner = team1 if r == 1 else team2
        return winner
    # if we are here, we have no winner after 3 death matches
    # just assign a random winner
    print('No winner after 3 Death Matches. Choose a winner at random:', wait=2)
    winner = random.choice((team1, team2))
    print('And the winner is', winner)
    return winner

def round1_ranking(config, rr_played):
    import collections
    points = collections.Counter()
    for match in rr_played:
        winner = match["winner"]
        if winner:
            points[match["winner"]] += POINTS_WIN
        else:
            for team in match["match"]:
                points[team] += POINTS_DRAW
    team_points = [(team_id, points[team_id]) for team_id in config.team_ids]
    return sorted(team_points, key=lambda elem: elem[1], reverse=True)

def pp_round1_results(config, rr_played):
    """Pretty print the current result of the matches."""
    print('Current Ranking:')
    for team_id, p in round1_ranking(config, rr_played):
        print("  %25s %d" % (config.team_name(team_id), p))
    print()

def round1(config, rr_unplayed, rr_played):
    """Run the first round and return a sorted list of team names.

    teams is the sorted list [group0, group1, ...] and not the actual names of
    the agents. This is necessary to start the agents.
    """
    wait_for_keypress()
    print()
    print("ROUND 1 (Everybody vs Everybody)")
    print('================================', speak=False)
    print()

    while rr_unplayed:
        match = rr_unplayed.pop()

        winner = start_match(config, match[0], match[1])

        if winner == 0:
            rr_played.append({ "match": match, "winner": False })
        else:
            rr_played.append({ "match": match, "winner": match[winner-1] })

        pp_round1_results(config, rr_played)

    return [team_id for team_id, p in round1_ranking(config, rr_played)]


def recur_match_winner(match):
    if isinstance(match, komode.Match) and match.winner is not None:
        return recur_match_winner(match.winner)
    elif isinstance(match, komode.Bye):
        return recur_match_winner(match.team)
    elif isinstance(match, komode.Team):
        return match.name
    elif isinstance(match, str):
        return match
    return None


def round2(config, teams):
    """Run the second round and return the name of the winning team.

    teams is the list [group0, group1, ...] not the names of the agens, sorted
    by the result of the first round.
    """
    print()
    print('ROUND 2 (K.O.)')
    print('==============', speak=False)
    print()
    wait_for_keypress()


    last_match = komode.prepare_matches(teams, bonusmatch=config.bonusmatch)
    tournament = komode.tree_enumerate(last_match)

    for round in tournament:
        for match in round:
            if isinstance(match, komode.Match):
                komode.print_knockout(last_match)
                match.winner = start_deathmatch(config,
                                                recur_match_winner(match.t1),
                                                recur_match_winner(match.t2))

    komode.print_knockout(last_match)

    wait_for_keypress()

    return last_match.winner


if __name__ == '__main__':
    # Command line argument parsing.
    # Oh, why must argparse be soo verbose :(
    parser = argparse.ArgumentParser(description='Run a tournament',
                                     add_help=False,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser._positionals = parser.add_argument_group('Arguments')
    parser.add_argument('pelitagame', help='The pelitagame script',
                        default=os.path.join(os.path.dirname(sys.argv[0]),
                                             '../pelitagame'),
                        nargs='?')
    parser._optionals = parser.add_argument_group('Options')
    parser.add_argument('--help', '-h',
                        help='show this help message and exit',
                        action='store_true')
    parser.add_argument('--speak', '-s',
                        help='speak loudly every messsage on stdout',
                        action='store_true')
    parser.add_argument('--rounds', '-r',
                        help='maximum number of rounds to play per match',
                        type=int, default=300)
    parser.add_argument('--viewer', '-v',
                        help='the pelita viewer to use', default='tk')
    parser.add_argument('--config', help='tournament data',
                        metavar="CONFIG_YAML", default="tournament.yaml")
    parser.add_argument('--interactive', help='ask before proceeding',
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
                    '--%s'%ARGS.viewer]

    # Check speaking support
    SPEAK = ARGS.speak and os.path.exists(FLITE)

    if not ARGS.no_log:
        # create a directory for the dumps
        DUMPSTORE = create_directory('./dumpstore')

        # open the log file (fail if it exists)
        logfile = os.path.join(DUMPSTORE, 'log')
        fd = os.open(logfile, os.O_CREAT|os.O_EXCL|os.O_WRONLY, 0o0666)
        LOGFILE = os.fdopen(fd, 'w')

    with open(ARGS.config) as f:
        global config
        config = Config(yaml.load(f))

    random.seed(config.seed)

    present_teams(config)

    state = {
        "round1": {
            "played": [],
            "unplayed": roundrobin.initial_state(config.team_ids)
        },
        "round2": {

        }
    }

    rr_ranking = round1(config, state["round1"]["unplayed"], state["round1"]["played"])
    if config.bonusmatch:
        sorted_ranking = komode.sort_ranks(rr_ranking[:-1]) + [rr_ranking[-1]]
    else:
        sorted_ranking = komode.sort_ranks(rr_ranking)

    winner = round2(config, sorted_ranking)

    print('The winner of the %s Pelita tournament is...' % config.location, wait=2, end=" ")
    print('{team_name}. Congratulations'.format(team_name=config.team_name(winner)), wait=2)
    print('Good evening master. It was a pleasure to serve you.')

