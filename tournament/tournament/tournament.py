#!/usr/bin/env python3
# -*- coding:utf-8 -*-

import argparse
import builtins
import io
import itertools
import json
import os
import random
import shlex
import sys
import tempfile
import time
from subprocess import PIPE, Popen, check_call

import yaml
import zmq

from pelita import libpelita
from . import roundrobin
from . import komode

_logger = libpelita.logging.getLogger("pelita-tournament.tournament")

# Tournament log file
DUMPSTORE = None

# Number of points a teams gets for matches in the first round
# Probably not worth it to make it options.
POINTS_DRAW = 1
POINTS_WIN = 2

SPEAK = True
LOGFILE = None

if os.name != 'posix':
    raise RuntimeError("Tournament can only run on Posix systems.")

# TODO: The PELITA_PATH environment variable tells pelita where to find the modules that
# in turn are able to run the user’s code.
os.environ["PELITA_PATH"] = os.environ.get("PELITA_PATH") or os.path.join(os.path.dirname(sys.argv[0]), "..")

def _print(*args, **kwargs):
    builtins.print(*args, **kwargs)
    if LOGFILE:
        kwargs['file'] = LOGFILE
        builtins.print(*args, **kwargs)

class Config:
    def __init__(self, config):
        self.teams = {}

        teams = config["teams"]
        # load team names
        for idx, team in enumerate(teams):
            team_id = team.get("id") or idx
            team_spec = team["spec"]
            team_name = set_name(team_spec)
            self.teams[team_id] = {
                "spec": team_spec,
                "name": team_name,
                "members": team["members"]
            }

        self.location = config["location"]
        self.date = config["date"]

        self.rounds = config.get("rounds")
        self.filter = config.get("filter")

        self.viewer = config.get("viewer")
        self.interactive = config.get("interactive")
        self.statefile = config.get("statefile")

        #: Global random seed.
        #: Keep it fixed or it may be impossible to replicate a tournament.
        #: Individual matches will get a random seed derived from this.
        self.seed = config.get("seed", 42)

        self.bonusmatch = config["bonusmatch"]

        self.speak = config.get("speak")
        self.speaker = config.get("speaker")

    @property
    def team_ids(self):
        return self.teams.keys()

    def team_name(self, team):
        return self.teams[team]["name"]

    def team_spec(self, team):
        return self.teams[team]["spec"]

    def print(self, *args, **kwargs):
        """Speak while you print. To disable set speak=False.
        You need the program %s to be able to speak.
        Set wait=X to wait X seconds after speaking."""
        if len(args) == 0:
            _print()
            return
        stream = io.StringIO()
        wait = kwargs.pop('wait', 0.5)
        want_speak = kwargs.pop('speak', SPEAK)
        if not want_speak or not self.speak:
            _print(*args, **kwargs)
        else:
            _print(*args, file=stream, **kwargs)
            string = stream.getvalue()
            _print(string, end='')
            sys.stdout.flush()
            with tempfile.NamedTemporaryFile('wt') as text:
                text.write(string+'\n')
                text.flush()
                festival = check_call([self.speaker, text.name])
            time.sleep(wait)

    def wait_for_keypress(self):
        if self.interactive:
            input('---\n')
        else:
            _logger.debug("Noninteractive. Not asking for keypress.")


class State:
    def __init__(self, config, state=None):
        if state is None:
            self.state = {
                "round1": {
                    "played": [],
                    "unplayed": roundrobin.initial_state(config.team_ids)
                },
                "round2": {}
            }
        else:
            self.state = state

    @property
    def round1(self):
        return self.state["round1"]

    @property
    def round2(self):
        return self.state["round2"]

    def save(self, filename):
        if filename:
            with open(filename, 'w') as f:
                yaml.dump(self.state, f, indent=2)

    @classmethod
    def load(cls, config, filename):
        if filename:
            with open(filename) as f:
                return cls(config=config, state=yaml.load(f))


def present_teams(config):
    config.print('Hello master, I am the Python drone. I am here to serve you.', wait=1.5)
    config.print('Welcome to the %s Pelita tournament %s' % (config.location, config.date), wait=1.5)
    config.print('This evening the teams are:', wait=1.5)
    for team_id, team in config.teams.items():
        if isinstance(team_id, int):
            team_id = "#{team_id}".format(team_id=team_id)
        config.print("{team_id}: {team_name}".format(team_id=team_id, team_name=team["name"]))
        for member in team["members"]:
            config.print("{member}".format(member=member), wait=0.1)
        # time.sleep(1)
        config.print()
    config.print('These were the teams. Now you ready for the fight?')


def set_name(team):
    """Get name of team."""
    try:
        team = libpelita.prepare_team(team)
        return libpelita.check_team(team)
    except Exception:
        print("*** ERROR: I could not load team {team}. Please help!".format(team=team))
        print(sys.stderr)
        raise


def run_match(config, teams):
    team1, team2 = teams

    ctx = zmq.Context()
    reply_addr = "ipc://tournament-reply#{pid}".format(pid=os.getpid())
    reply_sock = ctx.socket(zmq.PAIR)
    reply_sock.bind(reply_addr)

    rounds = ['--rounds', str(config.rounds)] if config.rounds else []
    filter = ['--filter', config.filter] if config.filter else []
    viewer = ['--' + config.viewer] if config.viewer else []

    cmd = [libpelita.get_python_process()] + ["./pelitagame"] + [config.team_spec(team1), config.team_spec(team2),
                              '--reply-to', reply_addr,
                              '--seed', str(random.randint(0, sys.maxsize)),
                              *filter,
                              *rounds,
                              *viewer]

    _logger.debug("Executing: {}".format(" ".join(shlex.quote(arg) for arg in cmd)))

    proc = Popen(cmd, stdout=PIPE, stderr=PIPE, universal_newlines=True, env=dict(os.environ, PYTHONUNBUFFERED='x'))


    # global ARGS
    # if not ARGS.no_log:
    #     dumpfile = os.path.join(DUMPSTORE, time.strftime('%Y%m%d-%H%M%S'))
    #     cmd += ['--dump', dumpfile]

    #if ARGS.dry_run:
    #    print("Would run: {cmd}".format(cmd=cmd))
    #    print("Choosing winner at random.")
    #    return random.choice([0, 1, 2])



    poll = zmq.Poller()
    poll.register(reply_sock, zmq.POLLIN)
    poll.register(proc.stdout.fileno(), zmq.POLLIN)
    poll.register(proc.stderr.fileno(), zmq.POLLIN)

    while True:
        evts = dict(poll.poll(1000))
        stdout_ready = (not proc.stdout.closed) and evts.get(proc.stdout.fileno(), False)
        if stdout_ready:
            line = proc.stdout.readline()
            if line:
                pass
                #print("STDOUT", line, end='')
            else:
                poll.unregister(proc.stdout.fileno())
                proc.stdout.close()
        stderr_ready = (not proc.stderr.closed) and evts.get(proc.stderr.fileno(), False)
        if stderr_ready:
            line = proc.stderr.readline()
            if line:
                pass
                #print("STDERR", line)
            else:
                poll.unregister(proc.stderr.fileno())
                proc.stderr.close()
        socket_ready = evts.get(reply_sock, False)
        if socket_ready:
            try:
                pelita_status = json.loads(reply_sock.recv_string())
                game_state = pelita_status['__data__']['game_state']
                finished = game_state.get("finished", None)
                team_wins = game_state.get("team_wins", None)
                game_draw = game_state.get("game_draw", None)
                if finished:
                    return game_state
            except json.JSONDecodeError:
                pass
            except KeyError:
                pass


def start_match(config, teams):
    """Start a match between a list of teams. Return the index of the team that won
    False if there was a draw.
    """
    assert len(teams) == 2
    team1, team2 = teams

    config.print()
    config.print('Starting match: '+ config.team_name(team1)+' vs ' + config.team_name(team2))
    config.print()
    config.wait_for_keypress()

    final_state = run_match(config, teams)
    game_draw = final_state['game_draw']
    team_wins = final_state['team_wins']

    if game_draw:
        config.print('‘{t1}’ and ‘{t2}’ had a draw.'.format(t1=config.team_name(team1),
                                                            t2=config.team_name(team2)))
        return False
    elif team_wins == 0 or team_wins == 1:
        winner = teams[team_wins]
        config.print('‘{team}’ wins'.format(team=config.team_name(winner)))
        return winner
    else:
        config.print("Unable to parse winning result :(")
        return None

    tmp = reversed(stdout.splitlines())
    for gameres in tmp:
        if gameres.startswith('Finished.'):
            config.print(gameres)
            break
    lastline = stdout.strip().splitlines()[-1]
    try:
        result = -1 if lastline == '-' else int(lastline)
    except ValueError:
        config.print("*** ERROR: Apparently the game crashed. At least I could not find the outcome of the game.")
        config.print("*** Maybe stdout helps you to debug the problem")
        print(stdout)
        config.print("*** Maybe stderr helps you to debug the problem")
        print(stderr)
        print("***")
        return None
    if stderr:
        config.print("***", stderr, speak=False)
    config.print('***', lastline)
    if lastline == '-':
        config.print('‘{t1}’ and ‘{t2}’ had a draw.'.format(t1=config.team_name(team1),
                                                            t2=config.team_name(team2)))
        return False
    elif lastline == '0':
        config.print('‘{t1}’ wins'.format(t1=config.team_name(team1)))
        return 0
    elif lastline == '1':
        config.print('‘{t2}’ wins'.format(t2=config.team_name(team2)))
        return 1
    else:
        config.print("Unable to parse winning result :(")
        return None


def start_deathmatch(config, team1, team2):
    """Start a match between team1 and team2 until one of them wins (ie no
    draw.)
    """
    config.print()
    config.print()
    config.print("{} v {}".format(config.team_name(team1), config.team_name(team2)))
    for i in range(3):
        winner = start_match(config, [team1, team2])
        if winner is False or winner is None:
            config.print('Draw -> Now go for a Death Match!')
            continue
        return winner
    # if we are here, we have no winner after 3 death matches
    # just assign a random winner
    config.print('No winner after 3 Death Matches. Choose a winner at random:', wait=2)
    winner = random.choice((team1, team2))
    config.print('And the winner is', config.team_name(winner))
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


def pp_round1_results(config, rr_played, rr_unplayed):
    """Pretty print the current result of the matches."""
    n_played = len(rr_played)
    es = "es" if n_played != 1 else ""
    n_togo = len(rr_unplayed)

    config.print()
    config.print('Ranking after {n_played} match{es} ({n_togo} to go):'.format(n_played=n_played, es=es, n_togo=n_togo))
    for team_id, p in round1_ranking(config, rr_played):
        config.print("  %25s %d" % (config.team_name(team_id), p))
    config.print()


def round1(config, state):
    """Run the first round and return a sorted list of team names.

    teams is the sorted list [group0, group1, ...] and not the actual names of
    the agents. This is necessary to start the agents.
    """
    rr_unplayed = state.round1["unplayed"]
    rr_played = state.round1["played"]

    config.wait_for_keypress()
    config.print()
    config.print("ROUND 1 (Everybody vs Everybody)")
    config.print('================================', speak=False)
    config.print()

    while rr_unplayed:
        match = rr_unplayed.pop()

        winner = start_match(config, match)

        if winner is False or winner is None:
            rr_played.append({ "match": match, "winner": False })
        else:
            rr_played.append({ "match": match, "winner": winner })

        pp_round1_results(config, rr_played, rr_unplayed)

        state.save(config.statefile)

    return [team_id for team_id, p in round1_ranking(config, rr_played)]


def recur_match_winner(match):
    if isinstance(match, komode.Match) and match.winner is not None:
        return recur_match_winner(match.winner)
    elif isinstance(match, komode.Bye):
        return recur_match_winner(match.team)
    elif isinstance(match, komode.Team):
        return match.name
    elif isinstance(match, str) or isinstance(match, int):
        return match
    return None


def round2(config, teams, state):
    """Run the second round and return the name of the winning team.

    teams is the list [group0, group1, ...] not the names of the agens, sorted
    by the result of the first round.
    """
    config.print()
    config.print('ROUND 2 (K.O.)')
    config.print('==============', speak=False)
    config.print()
    config.wait_for_keypress()

    tournament = state.round2.get("tournament")
    last_match = state.round2.get("last_match")
    if tournament and last_match:
        print("Loading from state.")
    else:
        last_match = komode.prepare_matches(teams, bonusmatch=config.bonusmatch)
        tournament = komode.tree_enumerate(last_match)

        state.round2["last_match"] = last_match
        state.round2["tournament"] = tournament

    for round in tournament:
        for match in round:
            if isinstance(match, komode.Match):
                if not match.winner:
                    print(komode.print_knockout(last_match, config.team_name))
                    winner = start_deathmatch(config,
                                              recur_match_winner(match.t1),
                                              recur_match_winner(match.t2))
                    match.winner = winner

                    state.round2["tournament"] = tournament
                    state.save(config.statefile)
                else:
                    config.print("Already played {match}. Skipping".format(match=match))

    print(komode.print_knockout(last_match, config.team_name))

    config.wait_for_keypress()

    return last_match.winner

