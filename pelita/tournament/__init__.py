import contextlib
from dataclasses import dataclass
import io
import json
import logging
import os
import re
import shlex
import signal
import subprocess
import sys
import tempfile
import time

import yaml
import zmq

from ..team import make_team
from . import knockout_mode, roundrobin

_logger = logging.getLogger(__name__)
_mswindows = (sys.platform == "win32")


# Number of points a teams gets for matches in the first round
# Probably not worth it to make it options.
POINTS_DRAW = 1
POINTS_WIN = 2

LOGFILE = None


def check_team(team_spec):
    """ Instantiates a team from a team_spec and returns its name """
    team, _zmq_context = make_team(team_spec)
    return team.team_name


@contextlib.contextmanager
def run_and_terminate_process(args, **kwargs):
    """ This serves as a contextmanager around `subprocess.Popen`, ensuring that
    after the body of the with-clause has finished, the process itself (and the
    process’s children) terminates as well.

    On Unix we try sending a SIGTERM before killing the process group but as
    afterwards we only wait on the first child, this means that the grand children
    do not get the chance to properly terminate.
    In cases where the first child has children that should properly close, the
    first child should catch SIGTERM with a signal handler and wait on its children.

    On Windows we send a CTRL_BREAK_EVENT to the whole process group and
    hope for the best. :)
    """

    _logger.debug(f"Executing: {shlex.join(args)}")

    try:
        if _mswindows:
            p = subprocess.Popen(args, **kwargs, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        else:
            p = subprocess.Popen(args, **kwargs, preexec_fn=os.setsid)
        yield p
        p.poll()
        if p.returncode is not None:
            _logger.debug(f"Subprocess exited with {p.returncode}.")
        else:
            _logger.debug(f"Subprocess has not exited yet.")
    finally:
        if _mswindows:
            _logger.debug("Sending CTRL_BREAK_EVENT to {proc} with pid {pid}.".format(proc=p, pid=p.pid))
            os.kill(p.pid, signal.CTRL_BREAK_EVENT)
        else:
            try:
                pgid = os.getpgid(p.pid)
                _logger.debug("Sending SIGTERM to pgid {pgid}.".format(pgid=pgid))
                os.killpg(pgid, signal.SIGTERM) # send sigterm, or ...
                try:
                    # It would be nicer to wait with os.waitid on the process group
                    # but that does not seem to exist on macOS.
                    p.wait(3)
                except subprocess.TimeoutExpired:
                    _logger.debug("Sending SIGKILL to pgid {pgid}.".format(pgid=pgid))
                    os.killpg(pgid, signal.SIGKILL) # send sigkill, or ...
            except ProcessLookupError:
                # did our process group vanish?
                # we try killing only the child process then
                _logger.debug("Sending SIGTERM to pid {pid}.".format(pid=p.pid))
                p.terminate()
                try:
                    p.wait(3)
                except subprocess.TimeoutExpired:
                    _logger.debug("Sending SIGKILL to pid {pid}.".format(pid=p.pid))
                    p.kill()


def call_pelita(team_specs, *, rounds, size, viewer, seed, team_infos=None, write_replay=False, store_output=False):
    """ Starts a new process with the given command line arguments and waits until finished.

    Returns
    =======
    tuple of (game_state, stdout, stderr)
    """
    team1, team2 = team_specs

    if team_infos is None:
        team_infos = [None, None]

    if seed is not None:
        if isinstance(seed, int):
            # convert to str
            seed = str(seed)
        elif isinstance(seed, str):
            # try that it can be converted to int
            try:
                int(seed)
            except ValueError:
                raise ValueError("seed must be an int, a string that can be converted to int or None.")
        else:
            raise ValueError("seed must be an int, a string that can be converted to int or None.")

    ctx = zmq.Context()
    reply_sock = ctx.socket(zmq.PAIR)

    addr = 'tcp://127.0.0.1'
    reply_port = reply_sock.bind_to_random_port(addr)
    reply_addr = 'tcp://127.0.0.1' + ':' + str(reply_port)

    rounds = ['--rounds', str(rounds)] if rounds else []
    size = ['--size', size] if size else []
    viewer = ['--' + viewer] if viewer else []
    seed = ['--seed', seed] if seed else []
    write_replay = ['--write-replay', write_replay] if write_replay else []
    store_output = ['--store-output', store_output] if store_output else []
    append_blue = ['--append-blue', team_infos[0]] if team_infos[0] else []
    append_red = ['--append-red', team_infos[1]] if team_infos[1] else []

    cmd = [sys.executable, '-m', 'pelita.scripts.pelita_main',
           team1, team2,
           '--reply-to', reply_addr,
           *append_blue,
           *append_red,
           *rounds,
           *size,
           *viewer,
           *seed,
           *write_replay,
           *store_output]

    # We need to run a process in the background in order to await the zmq events
    # stdout and stderr are written to temporary files in order to be more portable
    with tempfile.TemporaryFile(mode='w+t') as stdout_buf, tempfile.TemporaryFile(mode='w+t') as stderr_buf:
        # We use the environment variable PYTHONUNBUFFERED here to retrieve stdout without buffering
        with run_and_terminate_process(cmd, stdout=stdout_buf, stderr=stderr_buf,
                                            universal_newlines=True,
                                            env=dict(os.environ, PYTHONUNBUFFERED='x')) as proc:

            poll = zmq.Poller()
            poll.register(reply_sock, zmq.POLLIN)

            final_game_state = None

            while True:
                evts = dict(poll.poll(1000))

                if not evts and proc.poll() is not None:
                    # no more events and proc has finished.
                    # we break the loop
                    break

                socket_ready = evts.get(reply_sock, False)
                if socket_ready:
                    try:
                        game_state = json.loads(reply_sock.recv_string())
                        finished = game_state.get("gameover", None)
                        whowins = game_state.get("whowins", None)
                        if finished:
                            final_game_state = game_state
                            # The game in the subprocess has finished but the process
                            # may still be running.
                            # Give it a little time to finish writing everything.
                            # Once we exit the `with` statement, the subprocess will
                            # be terminated.
                            try:
                                proc.wait(1)
                            except subprocess.TimeoutExpired:
                                # It didn’t terminate in time by itself.
                                # We exit anyway.
                                pass
                            break
                    except ValueError:  # JSONDecodeError
                        pass
                    except KeyError:
                        pass

        stdout_buf.seek(0)
        stderr_buf.seek(0)
        return (final_game_state, stdout_buf.read(), stderr_buf.read())



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


@dataclass
class MatchID:
    """Small helper class to keep track of which match is played for better logging."""
    round: int = 1
    match: int = 1
    match_repeat: int = 1
    def __str__(self) -> str:
        if self.match_repeat == 1:
            return f'round{self.round}-match{self.match:02}'
        else:
            return f'round{self.round}-match{self.match:02}-repeat{self.match_repeat}'
    def next_round(self):
        # increase round, reset all other values
        self.round += 1
        self.match = 1
        self.match_repeat = 1
    def next_match(self):
        # increase match, keep round, reset repeat
        self.match += 1
        self.match_repeat = 1
    def next_repeat(self):
        # increase repeat, keep all other values
        self.match_repeat += 1


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
        self.size = config.get("size")

        self.viewer = config.get("viewer")
        self.interactive = config.get("interactive")
        self.statefile = config.get("statefile")

        self.greeting = config.get("greeting", "Hello")
        self.farewell = config.get("farewell", "Good evening")
        self.host = config.get("host", "host")

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

    def team_group(self, team):
        return f"group {team}"

    def team_name_group(self, team):
        return f"{self.team_name(team)} ({self.team_group(team)})"

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
                festival = subprocess.run(full_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
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
    def __init__(self, config, rng, state=None):
        if state is None:
            self.state = {
                "round1": {
                    "played": [],
                    "unplayed": roundrobin.create_matchplan(config.team_ids, rng=rng)
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
                return cls(config=config, state=yaml.load(f, Loader=yaml.FullLoader))


def present_teams(config):
    config.wait_for_keypress()
    print("\33[H\33[2J")  # clear the screen

    greeting = config.greeting
    host = config.host

    config.print(f'{greeting} {host}, I am the Python drone. I am here to serve you.', wait=1.5)
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
        return check_team(team)
    except Exception:
        print("*** ERROR: I could not load team {team}. Please help!".format(team=team))
        print(sys.stderr)
        raise


def play_game_with_config(config, teams, rng, *, match_id=None):
    team1, team2 = teams

    if config.tournament_log_folder:
        if match_id:
            log_folder = config.tournament_log_folder / f"{match_id}-{time.strftime('%Y%m%d-%H%M%S')}"
        else:
            log_folder = config.tournament_log_folder / f"match-{time.strftime('%Y%m%d-%H%M%S')}"
        log_folder.mkdir()
        replay_file = log_folder / 'replay'
        log_kwargs = {
            'write_replay': str(replay_file),
            'store_output': str(log_folder)
        }
    else:
        log_folder = None
        log_kwargs = {}

    seed = str(rng.randint(0, sys.maxsize))
    team_infos = [config.team_group(team1), config.team_group(team2)]

    res = call_pelita([config.team_spec(team1), config.team_spec(team2)],
                                rounds=config.rounds,
                                size=config.size,
                                viewer=config.viewer,
                                team_infos=team_infos,
                                seed=seed,
                                **log_kwargs)

    if log_folder:
        (_final_state, stdout, stderr) = res
        (log_folder / 'main.out').write_text(stdout)
        (log_folder / 'main.err').write_text(stderr)

    return res


def start_match(config, teams, rng, *, shuffle=False, match_id=None):
    """Start a match between a list of teams. Return the index of the team that won
    False if there was a draw.
    """
    assert len(teams) == 2
    # Should we insist that all teams be different in a match?
    # assert len(teams) == len(set(teams))

    if shuffle:
        rng.shuffle(teams)

    team1, team2 = teams

    config.print()
    config.print('Starting match: '+ config.team_name_group(team1)+' vs ' + config.team_name_group(team2))
    config.print()
    config.wait_for_keypress()

    (final_state, stdout, stderr) = play_game_with_config(config, teams, rng=rng, match_id=match_id)
    try:
        whowins = final_state['whowins']

        if whowins == 2:
            config.print('‘{t1}’ and ‘{t2}’ had a draw.'.format(t1=config.team_name(team1),
                                                                t2=config.team_name(team2)))
            return False
        elif whowins == 0 or whowins == 1:
            winner = teams[whowins]
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


def start_match_with_replay(config, match, rng, *, shuffle=False, match_id=None):
    """ Runs start_match until it returns a proper output or manual intervention. """

    winner = start_match(config, match, rng=rng, shuffle=shuffle, match_id=match_id)
    while winner is None:
        config.print("Do you want to re-play the game or enter a winner manually?")
        res = config.input("(r)e-play/(0){}/(1){}/(d)raw > ".format(config.team_name(match[0]),
                                                                    config.team_name(match[1])), values="r01d")
        if res == 'r':
            if match_id:
                # increase the repeat count
                match_id.next_repeat()
            winner = start_match(config, match, rng=rng, shuffle=shuffle, match_id=match_id)
        elif res == '0':
            winner = match[0]
        elif res == '1':
            winner = match[1]
        elif res == 'd':
            winner = False
    return winner


def start_deathmatch(config, team1, team2, rng, *, match_id=None):
    """Start a match between team1 and team2 until one of them wins (ie no
    draw.)
    """
    config.print()
    config.print()
    config.print("{} v {}".format(config.team_name(team1), config.team_name(team2)))
    for i in range(3):
        winner = start_match_with_replay(config, [team1, team2], rng=rng, shuffle=True, match_id=match_id)
        config.wait_for_keypress()

        if winner is False or winner is None:
            config.print('Draw -> Now go for a Death Match!')
            if match_id:
                match_id.next_repeat()
            continue
        return winner
    # if we are here, we have no winner after 3 death matches
    # just assign a random winner
    config.print('No winner after 3 Death Matches. Choose a winner at random:', wait=2)
    winner = rng.choice((team1, team2))
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


def play_round1(config, state, rng):
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


    match_id = MatchID(round=1)
    for played_match in rr_played:
        _logger.debug("Skipping played match {}.".format(played_match))
        match_id.next_match()
        t1_id, t2_id = played_match["match"]
        winner = played_match["winner"]
        if winner is False or winner is None:
            config.print("Already played match between {t1} and {t2}. (Draw.) Skipping.".format(t1=config.team_name_group(t1_id),
                                                                                                t2=config.team_name_group(t2_id)))
        else:
            config.print("Already played match between {t1} and {t2}. ({winner} won.) Skipping.".format(t1=config.team_name_group(t1_id),
                                                                                                        t2=config.team_name_group(t2_id),
                                                                                                        winner=config.team_name(winner)))

    if not rr_unplayed:
        pp_round1_results(config, rr_played, rr_unplayed)

    while rr_unplayed:
        match = rr_unplayed.pop()

        winner = start_match_with_replay(config, match, rng=rng, match_id=match_id)
        match_id.next_match()
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

    if isinstance(match, knockout_mode.Match) and match.winner is not None:
        return recur_match_winner(match.winner)
    elif isinstance(match, knockout_mode.Bye):
        return recur_match_winner(match.team)
    elif isinstance(match, knockout_mode.Team):
        return match.name
    elif isinstance(match, str) or isinstance(match, int):
        return match
    return None


def play_round2(config, teams, state, rng):
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
        last_match = knockout_mode.prepare_matches(teams, bonusmatch=config.bonusmatch)
        tournament = knockout_mode.tree_enumerate(last_match)

        state.round2["last_match"] = last_match
        state.round2["tournament"] = tournament

    config.print(knockout_mode.print_knockout(last_match, config.team_name), speak=False)

    match_id = MatchID(round=2, match=1)
    for round in tournament:
        for match in round:
            if isinstance(match, knockout_mode.Match):
                t1_id = recur_match_winner(match.t1)
                t2_id = recur_match_winner(match.t2)
                if not match.winner:
                    winner = start_deathmatch(config, t1_id, t2_id, rng=rng, match_id=match_id)
                    match.winner = winner

                    config.print(knockout_mode.print_knockout(last_match, config.team_name, highlight=[match]), speak=False)

                    state.round2["tournament"] = tournament
                    state.save(config.statefile)
                else:
                    _logger.debug("Skipping match {}.".format(match))
                    config.print("Already played match between {t1} and {t2}. ({winner} won.) Skipping.".format(t1=config.team_name_group(t1_id),
                                                                                                                t2=config.team_name_group(t2_id),
                                                                                                                winner=config.team_name(match.winner)))
                match_id.next_match()

    config.wait_for_keypress()

    return last_match.winner
