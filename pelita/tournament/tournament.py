#!/usr/bin/env python3
# -*- coding:utf-8 -*-

import builtins
import io
import json
import os
import random
import re
import shlex
import subprocess
import sys
import tempfile
import time

import yaml
import zmq

from pelita import libpelita
from . import roundrobin
from . import komode

_logger = libpelita.logging.getLogger("pelita-tournament")

# Number of points a teams gets for matches in the first round
# Probably not worth it to make it options.
POINTS_DRAW = 1
POINTS_WIN = 2

LOGFILE = None

if os.name != 'posix':
    raise RuntimeError("Tournament can only run on Posix systems.")


def create_team_id(team_id, idx):
    """ Checks that the team_id in the config is valid or else
    creates one from the given index. """
    if team_id is None:
        return "#" + str(idx)
    elif not isinstance(team_id, str):
        raise ValueError("team_id must be string or None.")
    elif not team_id:
        raise ValueError("team_id must not be empty.")
    elif team_id.startswith("#"):
        raise ValueError("team_id must not start with #.")
    else:
        return team_id


class Config:
    def __init__(self, config):
        self.teams = {}

        teams = config["teams"]
        # load team names
        for idx, team in enumerate(teams):
            team_id = create_team_id(team.get("id"), idx)
            team_spec = team["spec"]
            team_name = set_name(team_spec)

            if team_id in self.teams:
                raise ValueError("Duplicate team_id {} given.".format(team_id))

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

        self.tournament_log_folder = None
        self.tournament_log_file = None

    @property
    def team_ids(self):
        return self.teams.keys()

    def team_name(self, team):
        return self.teams[team]["name"]

    def team_spec(self, team):
        return self.teams[team]["spec"]

    def _print(self, *args, **kwargs):
        print(*args, **kwargs)
        if self.tournament_log_file:
            with open(self.tournament_log_file, 'a') as f:
                kwargs['file'] = f
                print(*args, **kwargs)

    def print(self, *args, **kwargs):
        """Speak while you print. To disable set speak=False.
        You need the program %s to be able to speak.
        Set wait=X to wait X seconds after speaking."""
        if len(args) == 0:
            self._print()
            return
        stream = io.StringIO()
        wait = kwargs.pop('wait', 0.5)
        want_speak = kwargs.pop('speak', None)
        if (want_speak is False) or not self.speak:
            self._print(*args, **kwargs)
        else:
            self._print(*args, file=stream, **kwargs)
            string = stream.getvalue()
            self._print(string, end='')
            sys.stdout.flush()
            self.say(string)
            time.sleep(wait)

    def say(self, string):
        with tempfile.NamedTemporaryFile('w+t') as tmp:
            ansi_seqs = re.compile(r'\x1b[^m]*m')
            string = ansi_seqs.sub('', string)

            tmp.write(string+'\n')
            tmp.flush()
            cmd = shlex.split(self.speaker)
            full_cmd = [*cmd, tmp.name]
            try:
                festival = subprocess.check_call(full_cmd)
            except FileNotFoundError:
                # If we could not find the executable then there is not need to keep on trying.
                # Disabling speak. (Although self.say() will still attempt to speak.)

                print("Could not find executable in call {!r}".format(full_cmd))
                print("Disabling speech synthesis.")

                _logger.warn("Could not find executable in call {!r}".format(full_cmd))
                _logger.warn("Disabling speech synthesis.")

                self.speak = False
                self.wait_for_keypress()
            except subprocess.CalledProcessError as err:
                # A non-zero return value could mean that the call syntax is wrong.
                # However, it could also be a one-time error (maybe the program did
                # not like a character in the string or something like that).
                # We only print the error the first time and only log it afterwards.

                if not getattr(self, '_say_process_error', False):
                    print(err)
                    print("Ignoring this error.")
                    self._say_process_error = True
                    self.wait_for_keypress()
                else:
                    _logger.warn(err)


    def input(self, str, values=None):
        if not values:
            values = []
        while True:
            res = input(str)
            try:
                if res[0] in values:
                    return res[0]
            except IndexError:
                pass


    def wait_for_keypress(self):
        if self.interactive:
            input('--- (press ENTER to continue) ---\n')
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
    config.wait_for_keypress()
    print("\33[H\33[2J")  # clear the screen
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
    if config.tournament_log_folder:
        dumpfile = os.path.join(config.tournament_log_folder, "dump-{time}".format(time=time.strftime('%Y%m%d-%H%M%S')))
        dump = ['--dump', dumpfile]
    else:
        dump = []

    cmd = [libpelita.get_python_process(), '-m', 'pelita.scripts.pelita_main'] + [config.team_spec(team1), config.team_spec(team2),
                              '--reply-to', reply_addr,
                              '--seed', str(random.randint(0, sys.maxsize)),
                              *dump,
                              *filter,
                              *rounds,
                              *viewer]

    _logger.debug("Executing: {}".format(libpelita.shlex_unsplit(cmd)))

    # We use the environment variable PYTHONUNBUFFERED here to retrieve stdout without buffering
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            universal_newlines=True, env=dict(os.environ, PYTHONUNBUFFERED='x'))


    #if ARGS.dry_run:
    #    print("Would run: {cmd}".format(cmd=cmd))
    #    print("Choosing winner at random.")
    #    return random.choice([0, 1, 2])


    poll = zmq.Poller()
    poll.register(reply_sock, zmq.POLLIN)
    poll.register(proc.stdout.fileno(), zmq.POLLIN)
    poll.register(proc.stderr.fileno(), zmq.POLLIN)

    with io.StringIO() as stdout_buf, io.StringIO() as stderr_buf:
        final_game_state = None

        while True:
            evts = dict(poll.poll(1000))

            if not evts and proc.poll() is not None:
                # no more events and proc has finished.
                # we give up
                break

            stdout_ready = (not proc.stdout.closed) and evts.get(proc.stdout.fileno(), False)
            if stdout_ready:
                line = proc.stdout.readline()
                if line:
                    print(line, end='', file=stdout_buf)
                else:
                    poll.unregister(proc.stdout.fileno())
                    proc.stdout.close()
            stderr_ready = (not proc.stderr.closed) and evts.get(proc.stderr.fileno(), False)
            if stderr_ready:
                line = proc.stderr.readline()
                if line:
                    print(line, end='', file=stderr_buf)
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
                        final_game_state = game_state
                        break
                except json.JSONDecodeError:
                    pass
                except KeyError:
                    pass

        return (final_game_state, stdout_buf.getvalue(), stderr_buf.getvalue())


def start_match(config, teams, shuffle=False):
    """Start a match between a list of teams. Return the index of the team that won
    False if there was a draw.
    """
    assert len(teams) == 2
    # Should we insist that all teams be different in a match?
    # assert len(teams) == len(set(teams))

    if shuffle:
        random.shuffle(teams)

    team1, team2 = teams

    config.print()
    config.print('Starting match: '+ config.team_name(team1)+' vs ' + config.team_name(team2))
    config.print()
    config.wait_for_keypress()

    (final_state, stdout, stderr) = run_match(config, teams)
    try:
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
            raise ValueError
    except (TypeError, ValueError, KeyError):
        config.print("Unable to parse winning result :(")
        config.print("*** ERROR: Apparently the game crashed. At least I could not find the outcome of the game.")
        config.print("*** Maybe stdout helps you to debug the problem")
        config.print(stdout, speak=False)
        config.print("*** Maybe stderr helps you to debug the problem")
        config.print(stderr, speak=False)
        config.print("***", speak=False)
        return None


def start_match_with_replay(config, match, shuffle=False):
    """ Runs start_match until it returns a proper output or manual intervention. """

    winner = start_match(config, match, shuffle=shuffle)
    while winner is None:
        config.print("Do you want to re-play the game or enter a winner manually?")
        res = config.input("(r)e-play/(0){}/(1){}/(d)raw > ".format(config.team_name(match[0]),
                                                                    config.team_name(match[1])), values="r01d")
        if res == 'r':
            winner = start_match(config, match, shuffle=shuffle)
        elif res == '0':
            winner = match[0]
        elif res == '1':
            winner = match[1]
        elif res == 'd':
            winner = False
    return winner


def start_deathmatch(config, team1, team2):
    """Start a match between team1 and team2 until one of them wins (ie no
    draw.)
    """
    config.print()
    config.print()
    config.print("{} v {}".format(config.team_name(team1), config.team_name(team2)))
    for i in range(3):
        winner = start_match_with_replay(config, [team1, team2], shuffle=True)
        config.wait_for_keypress()

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
        if winner is not False and winner is not None:
            points[match["winner"]] += POINTS_WIN
        else:
            for team in match["match"]:
                points[team] += POINTS_DRAW
    team_points = [(team_id, points[team_id]) for team_id in config.team_ids]
    return sorted(team_points, key=lambda elem: elem[1], reverse=True)


def pp_round1_results(config, rr_played, rr_unplayed, highlight=None):
    if highlight is None:
        highlight = []
    BOLD = '\033[1m'
    END = '\033[0m'

    """Pretty print the current result of the matches."""
    n_played = len(rr_played)
    es = "es" if n_played != 1 else ""
    n_togo = len(rr_unplayed)

    config.print()
    config.print('Ranking after {n_played} match{es} ({n_togo} to go):'.format(n_played=n_played, es=es, n_togo=n_togo))
    for team_id, p in round1_ranking(config, rr_played):
        if team_id in highlight:
            config.print("  {BOLD}{:>25}{END} {}".format(config.team_name(team_id), p, BOLD=BOLD, END=END))
        else:
            config.print("  {:>25} {}".format(config.team_name(team_id), p))
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

    for played_match in rr_played:
        _logger.debug("Skipping played match {}.".format(played_match))
        t1_id, t2_id = played_match["match"]
        winner = played_match["winner"]
        if winner is False or winner is None:
            config.print("Already played match between {t1} and {t2}. (Draw.) Skipping.".format(t1=config.team_name(t1_id),
                                                                                                t2=config.team_name(t2_id)))
        else:
            config.print("Already played match between {t1} and {t2}. ({winner} won.) Skipping.".format(t1=config.team_name(t1_id),
                                                                                                        t2=config.team_name(t2_id),
                                                                                                        winner=config.team_name(winner)))

    if not rr_unplayed:
        pp_round1_results(config, rr_played, rr_unplayed)

    while rr_unplayed:
        match = rr_unplayed.pop()

        winner = start_match_with_replay(config, match)
        config.wait_for_keypress()

        if winner is False or winner is None:
            rr_played.append({ "match": match, "winner": False })
        else:
            rr_played.append({ "match": match, "winner": winner })

        pp_round1_results(config, rr_played, rr_unplayed, highlight=match)

        state.save(config.statefile)

    return [team_id for team_id, p in round1_ranking(config, rr_played)]


def recur_match_winner(match):
    """ Returns the team id of the unambiguous winner.

    Parameters
    ----------
    match : one of Match, Bye, Team or a team id (str or int)
        Match to get the id for

    Returns
    -------
    team_id or None :
        The config id of the team.

    """

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
        config.print("Loading from state.", speak=False)
    else:
        last_match = komode.prepare_matches(teams, bonusmatch=config.bonusmatch)
        tournament = komode.tree_enumerate(last_match)

        state.round2["last_match"] = last_match
        state.round2["tournament"] = tournament

    config.print(komode.print_knockout(last_match, config.team_name), speak=False)

    for round in tournament:
        for match in round:
            if isinstance(match, komode.Match):
                t1_id = recur_match_winner(match.t1)
                t2_id = recur_match_winner(match.t2)
                if not match.winner:
                    winner = start_deathmatch(config, t1_id, t2_id)
                    match.winner = winner

                    config.print(komode.print_knockout(last_match, config.team_name, highlight=[match]), speak=False)

                    state.round2["tournament"] = tournament
                    state.save(config.statefile)
                else:
                    _logger.debug("Skipping match {}.".format(match))
                    config.print("Already played match between {t1} and {t2}. ({winner} won.) Skipping.".format(t1=config.team_name(t1_id),
                                                                                                                t2=config.team_name(t2_id),
                                                                                                                winner=config.team_name(match.winner)))


    config.wait_for_keypress()

    return last_match.winner


