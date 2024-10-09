#!/usr/bin/env python3

# Copyright (c) 2013, Bastian Venthur <venthur@debian.org>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the
#    distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""Continuous Integration Engine.

Currently this module is only usable as a script, later it shall be
extended to be used as a library for a web service providing a
continuous integration service.

In its current form it is still very usable to test a couple of agents
automatically against each other and compare the results. For best
results modify the ``agents`` section in the ``ci.cfg`` configuration
file and run this file. Leave it running for a while until the positions
stabilized.

"""


import configparser
import itertools
import json
import logging
import sqlite3
import subprocess
import sys
from random import Random

import click
from rich.console import Console
from rich.table import Table

from pelita.network import ZMQClientError
from pelita.tournament import check_team, call_pelita
from pelita.scripts.script_utils import start_logging

_logger = logging.getLogger(__name__)

# the path of the configuration file
CFG_FILE = './ci.cfg'

def hash_team(team_spec):
    external_call = [sys.executable,
                    '-m',
                    'pelita.scripts.pelita_player',
                    'hash-team',
                    team_spec]
    _logger.debug("Executing: %r", external_call)
    res = subprocess.run(external_call, capture_output=True, text=True)
    return res.stdout.strip().split("\n")[-1].strip()

class CI_Engine:
    """Continuous Integration Engine."""

    def __init__(self, cfgfile):
        self.players = []
        config = configparser.ConfigParser()
        config.read_file(cfgfile)
        for name, path in  config.items('agents'):
            self.players.append({'name': name, 'path': path})

        self.rounds = config['general'].getint('rounds', None)
        self.size = config['general'].get('size', None)
        self.viewer = config['general'].get('viewer', 'null')
        self.seed = config['general'].get('seed', None)

        self.db_file = config.get('general', 'db_file')
        self.dbwrapper = DB_Wrapper(self.db_file)

    def load_players(self):
        hash_cache = {}

        # remove players from db which are not in the config anymore
        for pname in self.dbwrapper.get_players():
            if pname not in [p['name'] for p in self.players]:
                _logger.debug('Removing %s from database, because it is not among the current players.' % (pname))
                self.dbwrapper.remove_player(pname)

        # add new players into db
        for player in self.players:
            pname, path = player['name'], player['path']
            if pname not in self.dbwrapper.get_players():
                _logger.debug('Adding %s to database.' % pname)
                hash_cache[path] = hash_team(path)
                self.dbwrapper.add_player(pname, hash_cache[path])

        # reset players where the directory hash changed
        for player in self.players:
            path = player['path']
            pname = player['name']
            new_hash = hash_cache.get(path, hash_team(path))
            if new_hash != self.dbwrapper.get_player_hash(pname):
                _logger.debug('Resetting %s because its module hash changed.' % pname)
                self.dbwrapper.remove_player(pname)
                self.dbwrapper.add_player(pname, new_hash)

        for player in self.players:
            path = player['path']
            pname = player['name']
            try:
                _logger.debug('Querying team name for %s.' % pname)
                team_name = check_team(player['path'])
                self.dbwrapper.add_team_name(pname, team_name)
            except ZMQClientError as e:
                e_type, e_msg = e.args
                _logger.debug(f'Could not import {player} at path {path} ({e_type}): {e_msg}')
                player['error'] = e.args

    def run_game(self, p1, p2):
        """Run a single game.

        This method runs a single game ``p1`` vs ``p2`` and internally
        stores the result.

        Parameters
        ----------
        p1, p2 : int
            the indices of the players

        """
        team_specs = [self.players[i]['path'] for i in (p1, p2)]
        print(f"Playing {self.players[p1]['name']} against {self.players[p2]['name']}.")

        final_state, stdout, stderr = call_pelita(team_specs,
                                                            rounds=self.rounds,
                                                            size=self.size,
                                                            viewer=self.viewer,
                                                            seed=self.seed)

        if final_state['whowins'] == 2:
            result = -1
        else:
            result = final_state['whowins']

        del final_state['walls']
        del final_state['food']

        _logger.info('Final state: %r', final_state)
        _logger.debug('Stdout: %r', stdout)
        if stderr:
            _logger.warning('Stderr: %r', stderr)
        p1_name, p2_name = self.players[p1]['name'], self.players[p2]['name']
        self.dbwrapper.add_gameresult(p1_name, p2_name, result, final_state, stdout, stderr)


    def start(self, n):
        """Start the Engine.

        This method will start and infinite loop, testing each agent
        randomly against another one. The result is printed after each
        game.

        Currently the only way to stop the engine is via CTRL-C.

        Examples
        --------
        >>> ci = CI_Engine()
        >>> ci.start()

        """
        loop = itertools.repeat(None) if n == 0 else itertools.repeat(None, n)
        rng = Random()

        for _ in  loop:
            # choose the player with the least number of played game,
            # mix him with another random player
            # mis the sides and let them play
            broken_players = {idx for idx, player in enumerate(self.players) if player.get('error')}
            game_count = [(self.dbwrapper.get_game_count(p['name']), idx) for idx, p in enumerate(self.players)]
            players_sorted = [idx for count, idx in sorted(game_count) if not idx in broken_players]
            a, rest = players_sorted[0], players_sorted[1:]
            b = rng.choice(rest)
            players = [a, b]
            rng.shuffle(players)

            self.run_game(players[0], players[1])
            self.pretty_print_results(highlight=[self.players[players[0]]['name'], self.players[players[1]]['name']])
            print('------------------------------')


    def get_results(self, idx, idx2=None):
        """Get the results so far.

        This method goes through the internal list of of all game
        results and calculates the result for the player with index
        ``idx`` against everyone else.

        If the optional argument ``idx2`` is given only the results of
        the players ``idx`` vs ``idx2`` are returned.

        Parameters
        ----------
        idx : int
            the index of the player
        idx2 : int, optional
            the index of the second player if this parameter is not
            given the result of player against all other players is
            returned otherwise the results of the games of the players
            with the indices ``idx`` and ``idx2`` are returned


        Returns
        -------
        win, loss, draw : int
            the number of wins, losses and draws for this player or
            combination of players


        Examples
        --------

        >>> # get the results of player with index 1 against all other
        >>> # players
        >>> ci.get_results(1)
        (5, 2, 0)
        >>> # get the results of all games with the players of index 1
        >>> # and 5
        >>> ci.get_results(1, 5)
        (2, 0, 0)

        """
        win, loss, draw = 0, 0, 0
        p1_name = self.players[idx]['name']
        p2_name = None if idx2 == None else self.players[idx2]['name']
        relevant_results = self.dbwrapper.get_results(p1_name, p2_name)
        for p1, p2, r in relevant_results:
            if (idx2 is None and p1_name == p1) or (idx2 is not None and p1_name == p1 and p2_name == p2):
                if r == 0: win += 1
                elif r == 1: loss += 1
                elif r == -1: draw += 1
            if (idx2 is None and p1_name == p2) or (idx2 is not None and p1_name == p2 and p2_name == p1):
                if r == 1: win += 1
                elif r == 0: loss += 1
                elif r == -1: draw += 1
        return win, loss, draw

    def get_errorcount(self, idx):
        """Gets the error count for team idx

        Parameters
        ----------
        idx : int
            the index of the player

        Returns
        -------
        error_count, fatalerror_count : int
            the number of errors for this player

        """
        p_name = self.players[idx]['name']
        error_count, fatalerror_count = self.dbwrapper.get_errorcount(p_name)
        return error_count, fatalerror_count

    def get_team_name(self, idx):
        """Get last registered team name.

        team_name : string
        """

        p_name = self.players[idx]['name']
        return self.dbwrapper.get_team_name(p_name)

    def gen_elo(self):
        k = 32

        def elo_change(a, b, outcome):
            expected = 1 / ( 10**((b - a) / 400) + 1 )
            return k * (outcome - expected)

        from collections import defaultdict
        elo = defaultdict(lambda: 1500)

        g = self.dbwrapper.cursor.execute("""
        SELECT player1, player2, result
        FROM games
        """).fetchall()
        for p1, p2, result in g:
            if result == 0:
                change = elo_change(elo[p1], elo[p2], 1)
            if result == 1:
                change = elo_change(elo[p1], elo[p2], 0)
            if result == -1:
                change = elo_change(elo[p1], elo[p2], 0.5)
            elo[p1] += change
            elo[p2] -= change

        return elo

    def pretty_print_results(self, highlight=None):
        """Pretty print the current results.

        """
        if highlight is None:
            highlight = []

        console = Console()
        # Some guesswork in here
        MAX_COLUMNS = (console.width - 40) // 12
        if MAX_COLUMNS < 4:
            # Let’s be honest: You should enlarge your terminal window even before that
            MAX_COLUMNS = 4

        res = self.dbwrapper.get_wins_losses()
        rows = { k: list(v) for k, v in itertools.groupby(res, key=lambda x:x[0]) }

        good_players = [p for p in self.players if not p.get('error')]
        bad_players = [p for p in self.players if p.get('error')]

        num_rows_per_player = (len(good_players) // MAX_COLUMNS) + 1
        row_style = [*([""] * num_rows_per_player), *(["dim"] * num_rows_per_player)]

        table = Table(row_styles=row_style, title="Cross results")
        table.add_column("")
        table.add_column("Name")
        table.add_column("Score", justify="right")
        table.add_column("W/D/L")

        column_players = [[] for _idx in range(min(MAX_COLUMNS, len(good_players)))]
        # if we have more good_players than allowed columns, we must wrap around
        for idx, _p in enumerate(good_players):
            column_players[idx % MAX_COLUMNS].append(idx)

        for midx in column_players:
            table.add_column('\n'.join(map(str, midx)))


        def batched(iterable, n):
            # Backport from Python 3.12
            # batched('ABCDEFG', 3) → ABC DEF G
            if n < 1:
                raise ValueError('n must be at least one')
            iterator = iter(iterable)
            while batch := tuple(itertools.islice(iterator, n)):
                yield batch

        result = []
        for idx, p in enumerate(good_players):
            win, loss, draw = self.get_results(idx)
            error_count, fatalerror_count = self.get_errorcount(idx)
            try:
                team_name = self.get_team_name(idx)
            except ValueError:
                team_name = None
            score = 0 if (win+loss+draw) == 0 else (win-loss) / (win+loss+draw)
            result.append([score, win, draw, loss, p['name'], team_name, error_count, fatalerror_count])
            wdl = f"{win:3d},{draw:3d},{loss:3d}"

            try:
                row = rows[p['name']]
            except KeyError:
                continue
            vals = { k: (w,l,d) for _p1, k, w, l, d in row }

            cross_results = []
            for idx2, p2 in enumerate(good_players):
                win, loss, draw = vals.get(p2['name'], (0, 0, 0))
                if idx == idx2:
                    cross_results.append("  - - - ")
                else:
                    cross_results.append(f"{win:2d},{draw:2d},{loss:2d}")

            for c, r in enumerate(batched(cross_results, MAX_COLUMNS)):
                if c == 0:
                    table.add_row(f"{idx}", p['name'], f"{score:.2f}", wdl, *r)
                else:
                    table.add_row("", "", "", "", *r)

        console.print(table)

        table = Table(title="Bot ranking")

        table.add_column("Name")
        table.add_column("# Matches")
        table.add_column("# Wins")
        table.add_column("# Draws")
        table.add_column("# Losses")
        table.add_column("Score")
        table.add_column("ELO")
        table.add_column("Error count")
        table.add_column("# Fatal Errors")

        elo = self.gen_elo()

        result.sort(reverse=True)
        for [score, win, draw, loss, name, team_name, error_count, fatalerror_count] in result:
            style = "bold" if name in highlight else None
            display_name = f"{name} ({team_name})" if team_name else f"{name}"
            table.add_row(
                display_name,
                f"{win+draw+loss}",
                f"{win}",
                f"{draw}",
                f"{loss}",
                f"{score:6.3f}",
                f"{elo[name]: >4.0f}",
                f"{error_count}",
                f"{fatalerror_count}",
                style=style,
            )

        console.print(table)

        for p in bad_players:
            print("% 30s ***%30s***" % (p['name'], p['error']))


class DB_Wrapper:
    """Wrapper around the games database."""

    def __init__(self, dbfile):
        """Initialize the connection to the db ``dbfile``.

        Create table if file does not exist.

        Parameters
        ----------
        dbfile : str
            path to sqlite3 database

        """
        self.db_file = dbfile
        self.connection = sqlite3.connect(self.db_file)
        self.cursor = self.connection.cursor()
        self.cursor.execute("PRAGMA foreign_keys = ON;")
        self.create_tables()

    def create_tables(self):
        """Create tables.

        This is a no-op if the tables already exist.

        """
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS players
        (name text PRIMARY KEY, hash text)
        """)
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS team_names
        (name text PRIMARY KEY, team_name text,
        FOREIGN KEY(name) REFERENCES players(name) ON DELETE CASCADE)
        """)
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS games
        (player1 text, player2 text, result int, final_state text, stdout text, stderr text,
        FOREIGN KEY(player1) REFERENCES players(name) ON DELETE CASCADE,
        FOREIGN KEY(player2) REFERENCES players(name) ON DELETE CASCADE)
        """)
        self.connection.commit()

    def get_players(self):
        """Get players from the database.

        Returns
        -------
        players : list of strings
            the player names from the database.

        """
        players = self.cursor.execute("""SELECT name FROM players""").fetchall()
        players = [row[0] for row in players]
        return players

    def get_player_hash(self, name):
        """Get the hash stored in the database for the player.

        Raises
        ------
        ValueError : if the player does not exist in the database

        """
        h = self.cursor.execute("""
        SELECT hash
        FROM players
        WHERE name = ?
        """, (name,)).fetchone()
        if h is None:
            raise ValueError('Player %s does not exist in database.' % name)
        return h[0]

    def add_player(self, name, h):
        """Add player to database

        Parameters
        ----------
        name : str
        h : str
            hash of the player's directory

        Raises
        ------
        ValueError : if player already exists in database

        """
        try:
            self.cursor.execute("""
            INSERT INTO players
            VALUES (?, ?)
            """, [name, h])
            self.connection.commit()
        except sqlite3.IntegrityError:
            raise ValueError('Player %s already exists in database' % name)

    def add_team_name(self, name, team_name):
        """Adds or updates team name to database

        Parameters
        ----------
        name : str
        team_name : str

        """
        try:
            self.cursor.execute("""
            INSERT OR REPLACE INTO team_names
            VALUES (?, ?)
            """, [name, team_name])
            self.connection.commit()
        except sqlite3.IntegrityError:
            raise ValueError('Cannot add team name for %s' % name)

    def remove_player(self, pname):
        """Remove a player from the database.

        Removes all games where the player ``pname`` participated.

        Parameters
        ----------
        pname : str
            the player name of the player to be removed

        """
        self.cursor.execute("""DELETE FROM games
        WHERE player1 = ? or player2 = ?""", (pname, pname))
        self.cursor.execute("""DELETE FROM players
        WHERE name = ?""", (pname,))
        self.connection.commit()

    def add_gameresult(self, p1_name, p2_name, result, final_state, std_out, std_err):
        """Add a new game result to the database.

        Parameters
        ----------
        p1_name, p2_name : str
            the names of the players
        result : 0, 1 or -1
            0 if player 1 won
            1 of player 2 won
            -1 if draw
        std_out, std_err : str
            STDOUT and STDERR of the game

        """
        self.cursor.execute("""
        INSERT INTO games
        VALUES (?, ?, ?, ?, ?, ?)
        """, [p1_name, p2_name, result, json.dumps(final_state), std_out, std_err])
        self.connection.commit()

    def get_results(self, p1_name, p2_name=None):
        """Get all games involving player1 (AND player2 if specified).

        Parameters
        ----------
        p1_name : str
            the  name of player 1
        p2_name : str, optional
            the name of player 2, if not specified ``get_results`` will
            return all games involving player 1 otherwise it will return
            all games of player1 AND player2

        Returns
        -------
        relevant_results : list of gameresults

        """
        if p2_name is None:
            self.cursor.execute("""
            SELECT player1, player2, result FROM games
            WHERE player1 = ? or player2 = ?""", (p1_name, p1_name))
            relevant_results = self.cursor.fetchall()
        else:
            self.cursor.execute("""
            SELECT player1, player2, result FROM games
            WHERE (player1 = :p1 and player2 = :p2) or (player1 = :p2 and player2 = :p1)""",
            dict(p1=p1_name, p2=p2_name))
            relevant_results = self.cursor.fetchall()
        return relevant_results


    def get_team_name(self, p_name):
        """Gets the last registered team name of p_name.

        Parameters
        ----------
        p_name : str
            the name of the player

        Returns
        -------
        team_name : str

        """
        self.cursor.execute("""
        SELECT team_name FROM team_names
        WHERE name = ?""", (p_name,))
        res = self.cursor.fetchone()
        if res is None:
            raise ValueError('Player %s does not exist in database.' % p_name)
        return res[0]

    def get_game_count(self, p1_name, p2_name=None):
        """Get number of games involving player1 (AND player2 if specified).

        Parameters
        ----------
        p1_name : str
            the  name of player 1
        p2_name : str, optional
            the name of player 2, if not specified ``get_results`` will
            return all games involving player 1 otherwise it will return
            all games of player1 AND player2

        Returns
        -------
        relevant_results : list of gameresults

        """
        if p2_name is None:
            self.cursor.execute("""
            SELECT count(*) FROM games
            WHERE player1 = ? or player2 = ?""", (p1_name, p1_name))
            count, = self.cursor.fetchone()
        else:
            self.cursor.execute("""
            SELECT count(*) FROM games
            WHERE (player1 = :p1 and player2 = :p2) or (player1 = :p2 and player2 = :p1)""",
            dict(p1=p1_name, p2=p2_name))
            count, = self.cursor.fetchone()
        return count

    def get_errorcount(self, p1_name):
        """Get errorcount of player1

        Parameters
        ----------
        p1_name : str
            the  name of player 1

        Returns
        -------
        error_count, fatalerror_count : errorcount

        """
        self.cursor.execute("""
        SELECT sum(c) FROM
            (
                SELECT sum(json_extract(final_state, '$.num_errors[0]')) AS c
                FROM games
                WHERE player1 = :p1

                UNION ALL

                SELECT sum(json_extract(final_state, '$.num_errors[1]')) AS c
                FROM games
                WHERE player2 = :p1
            )
        """,
        dict(p1=p1_name))
        error_count, = self.cursor.fetchone()

        self.cursor.execute("""
        SELECT sum(c) FROM
            (
                SELECT count(*) AS c
                FROM games
                WHERE player1 = :p1 AND
                      json_extract(final_state, '$.fatal_errors[0]') != '[]'

                UNION ALL

                SELECT count(*) AS c
                FROM games
                WHERE player2 = :p1 AND
                      json_extract(final_state, '$.fatal_errors[1]') != '[]'
            )
        """,
        dict(p1=p1_name))
        fatal_errorcount, = self.cursor.fetchone()

        return error_count, fatal_errorcount

    def get_wins_losses(self, team=None):
        """ Get all wins and losses combined in a table of
        team | opponent | wins | losses | draws
        """

        if team is not None:
            where_clause = "WHERE team = ?"
        else:
            where_clause = ""

        query = f"""

        SELECT
            team, opponent, SUM(wins) AS wins, SUM(losses) AS losses, SUM(draws) AS draws
        FROM (
            -- Count wins for player1
            SELECT
                player1 AS team, player2 AS opponent, COUNT(*) AS wins, 0 AS losses, 0 AS draws
            FROM games
            WHERE result = 0
            GROUP BY player1, player2

            UNION ALL

            -- Count wins for player2
            SELECT
                player2 AS team, player1 AS opponent, 0 AS wins, COUNT(*) AS losses, 0 AS draws
            FROM games
            WHERE result = 0
            GROUP BY player2, player1

            UNION ALL

            -- Count losses for player1
            SELECT
                player1 AS team, player2 AS opponent, 0 AS wins, COUNT(*) AS losses, 0 AS draws
            FROM games
            WHERE result = 1
            GROUP BY player1, player2

            UNION ALL

            -- Count losses for player2
            SELECT
                player2 AS team, player1 AS opponent, COUNT(*) AS wins, 0 AS losses, 0 AS draws
            FROM games
            WHERE result = 1
            GROUP BY player2, player1

            UNION ALL

            -- Count draws for both teams
            SELECT
                player1 AS team, player2 AS opponent, 0 AS wins, 0 AS losses, COUNT(*) AS draws
            FROM games
            WHERE result = -1
            GROUP BY player1, player2

            UNION ALL

            SELECT
                player2 AS team, player1 AS opponent, 0 AS wins, 0 AS losses, COUNT(*) AS draws
            FROM games
            WHERE result = -1
            GROUP BY player2, player1
        ) AS results
        {where_clause}
        GROUP BY
            team, opponent
        ORDER BY
            team, opponent
        ;
        """
        if team is not None:
            return self.cursor.execute(query, [team]).fetchall()
        else:
            return self.cursor.execute(query).fetchall()


@click.command()
@click.option('--log',
              is_flag=False, flag_value="-", default=None, metavar='LOGFILE',
              help="print debugging log information to LOGFILE (default 'stderr')")
@click.option('--config',
              default=CFG_FILE,
              type=click.File('r'),
              help='Configuration file')
@click.option('-n', help='run N times', type=int, default=0)
@click.option('--print', is_flag=True, default=False,
              help='Print scores and exit.')
@click.option('--nohash', is_flag=True, default=False,
              help='Do not hash the players')
def main(log, config, n, print, nohash):
    if log is not None:
        start_logging(log, __name__)
        start_logging(log, 'pelita')

    ci_engine = CI_Engine(config)
    if print:
        ci_engine.pretty_print_results()
    else:
        if not nohash:
            ci_engine.load_players()
        ci_engine.start(n)

if __name__ == '__main__':
    main()
