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
import argparse
import hashlib
import logging
import os
from pathlib import Path
from modulefinder import ModuleFinder
import random
import sqlite3
import sys
import unittest

from pelita.network import ZMQClientError
from pelita.tournament import check_team, call_pelita

parser = argparse.ArgumentParser()
parser.add_argument('-t', '--test', help="run unittests", action="store_true")
parser.add_argument('-n', help="run N times", type=int, default=0)
args = parser.parse_args()

logging.basicConfig(format='%(relativeCreated)10.0f %(levelname)8s %(message)s', level=logging.NOTSET)
logger = logging.getLogger(__name__)
logger.info('Logger started')

# the path of the configuration file
CFG_FILE = './ci.cfg'


class CI_Engine:
    """Continuous Integration Engine.


    """

    def __init__(self, cfgfile=CFG_FILE):
        self.players = []
        config = configparser.ConfigParser()
        config.read(os.path.abspath(cfgfile))
        for name, path in  config.items('agents'):
            if name == '*':
                import glob
                paths = glob.glob(path)
                for p in paths:
                    if os.path.basename(p).startswith('_') or os.path.basename(p).startswith('.'):
                        continue
                    self.players.append({'name': os.path.basename(p),
                                         'path': p
                    })
            else:
                self.players.append({'name' : name,
                                     'path' : path
                                     })
#            else:
#                logger.warning('%s seems not to be an existing directory, ignoring %s' % (path, name))

        self.rounds = config['general'].getint('rounds', None)
        self.size = config['general'].get('size', None)
        self.viewer = config['general'].get('viewer', 'null')
        self.seed = config['general'].get('seed', None)

        self.db_file = config.get('general', 'db_file')
        self.dbwrapper = DB_Wrapper(self.db_file)
        # remove players from db which are not in the config anymore
        for pname in self.dbwrapper.get_players():
            if pname not in [p['name'] for p in self.players]:
                logger.debug('Removing %s from data base, because he is not among the current players.' % (pname))
                self.dbwrapper.remove_player(pname)
        # add new players into db
        for player in self.players:
            pname, path = player['name'], player['path']
            if pname not in self.dbwrapper.get_players():
                logger.debug('Adding %s to data base.' % pname)
                self.dbwrapper.add_player(pname, hashpath(path))

        # reset players where the directory hash changed
        for player in self.players:
            path = player['path']
            name = player['name']
            new_hash = hashpath(path)
            if new_hash != self.dbwrapper.get_player_hash(name):
                logger.debug('Resetting %s because its module hash changed.' % name)
                self.dbwrapper.remove_player(name)
                self.dbwrapper.add_player(pname, hashpath(path))

        for player in self.players:
            try:
                check_team(player['path'])
            except ZMQClientError as e:
                e_type, e_msg = e.args
                logger.debug(f'Could not import {pname} ({e_type}): {e_msg}')
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

        final_state, stdout, stderr = call_pelita(team_specs,
                                                            rounds=self.rounds,
                                                            size=self.size,
                                                            viewer=self.viewer,
                                                            seed=self.seed)

        if final_state['whowins'] == 2:
            result = -1
        else:
            result = final_state['whowins']

        logger.info('Final state: %r', final_state)
        logger.debug('Stdout: %r', stdout)
        if stderr:
            logger.warning('Stderr: %r', stderr)
        p1_name, p2_name = self.players[p1]['name'], self.players[p2]['name']
        self.dbwrapper.add_gameresult(p1_name, p2_name, result, stdout, stderr)


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
        import itertools
        loop = itertools.repeat(None) if n == 0 else itertools.repeat(None, n)

        for _ in  loop:
            # choose the player with the least number of played game,
            # mix him with another random player
            # mis the sides and let them play
            broken_players = {idx for idx, player in enumerate(self.players) if player.get('error')}
            game_count = [[sum(self.get_results(i)), i] for i in range(len(self.players))]
            players_sorted = [idx for count, idx in sorted(game_count) if not idx in broken_players]
            a, rest = players_sorted[0], players_sorted[1:]
            b = random.choice(rest)
            players = [a, b]
            random.shuffle(players)
            self.run_game(players[0], players[1])
            self.pretty_print_results()
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
        for p1, p2, r, std_out, std_err in relevant_results:
            if (idx2 is None and p1_name == p1) or (idx2 is not None and p1_name == p1 and p2_name == p2):
                if r == 0: win += 1
                elif r == 1: loss += 1
                elif r == -1: draw += 1
            if (idx2 is None and p1_name == p2) or (idx2 is not None and p1_name == p2 and p2_name == p1):
                if r == 1: win += 1
                elif r == 0: loss += 1
                elif r == -1: draw += 1
        return win, loss, draw


    def pretty_print_results(self):
        """Pretty print the current results.

        """
        good_players = [p for p in self.players if not p.get('error')]
        bad_players = [p for p in self.players if p.get('error')]
        print(' ' * 41 + ''.join("            % 2i" % idx for idx, p in enumerate(good_players)))
        result = []
        for idx, p in enumerate(good_players):
            win, loss, draw = self.get_results(idx)
            score = 0 if (win+loss+draw) == 0 else (win-loss) / (win+loss+draw)
            result.append([score, p['name']])
            print('% 2i: %17s (%6.2f): %3d,%3d,%3d  ' % (idx, p['name'][0:17], score, win, loss, draw), end=' ')
            for idx2, p2 in enumerate(good_players):
                win, loss, draw = self.get_results(idx, idx2)
                print('  %3d,%3d,%3d' % (win, loss, draw), end=' ')
            print()
        print()
        result.sort(reverse=True)
        for [score, name] in result:
            print("% 30s %6.2f" % (name, score))
        for p in bad_players:
            print("% 30s ***%30s***" % (p['name'], p['error']))


class DB_Wrapper:
    """Wrapper around the games data base."""

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
        CREATE TABLE IF NOT EXISTS games
        (player1 text, player2 text, result int, stdout text, stderr text,
        FOREIGN KEY(player1) REFERENCES players(name) ON DELETE CASCADE,
        FOREIGN KEY(player2) REFERENCES players(name) ON DELETE CASCADE)
        """)
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS players
        (name text PRIMARY KEY, hash text)
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
        """Get the hash stored in the data base for the player.

        Raises
        ------
        ValueError : if the player does not exist in the data base

        """
        h = self.cursor.execute("""
        SELECT hash
        FROM players
        WHERE name = ?
        """, (name,)).fetchone()
        if h is None:
            raise ValueError('Player %s does not exist in data base.' % name)
        return h[0]

    def add_player(self, name, h):
        """Add player to data base

        Parameters
        ----------
        name : str
        h : str
            hash of the player's directory

        Raises
        ------
        ValueError : if player already exists in data base

        """
        try:
            self.cursor.execute("""
            INSERT INTO players
            VALUES (?, ?)
            """, [name, h])
            self.connection.commit()
        except sqlite3.IntegrityError:
            raise ValueError('Player %s already exists in data base' % name)

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

    def add_gameresult(self, p1_name, p2_name, result, std_out, std_err):
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
        VALUES (?, ?, ?, ?, ?)
        """, [p1_name, p2_name, result, std_out, std_err])
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
            SELECT * FROM games
            WHERE player1 = ? or player2 = ?""", (p1_name, p1_name))
            relevant_results = self.cursor.fetchall()
        else:
            self.cursor.execute("""
            SELECT * FROM games
            WHERE (player1 = :p1 and player2 = :p2) or (player1 = :p2 and player2 = :p1)""",
            dict(p1=p1_name, p2=p2_name))
            relevant_results = self.cursor.fetchall()
        return relevant_results


def hashpath(pathname):
    """If given a directory, calculate the SHA1 sum of its contents.
    If given a Python script, calculate the SHA1 sum of all of its (relative)
    module imports.

    Parameters
    ----------
    pathname : str
        the path of the directory or the Python script to check

    Returns
    -------
    hexdigest : str
        the SHA1

    Examples
    --------

    >>> hashpath('/tmp')
    'cac36aaf1c64d7f93c9d874471f23de1cbfd5249'
    >>> hashpath('demo01_stopping.py')
    'd2c07aafb6fbf2474f3b38e3baf4bb931994d844'
    """
    if Path(pathname).is_dir():
        return hashdir(pathname)
    else:
        return hashmodule(pathname)

def hashdir(pathname):
    """Calculate the SHA1 sum of the contents of a directory.

    It operates by walking through the directory, collecting all
    filenames, sorting them alphabetically and calculating the SHA1 of
    the contents of the files.

    Parameters
    ----------
    pathname : str
        the path of the directory to check

    Returns
    -------
    hexdigest : str
        the SHA1

    Examples
    --------

    >>> hashdir('/tmp')
    'cac36aaf1c64d7f93c9d874471f23de1cbfd5249'

    """
    files = []
    for path, root, filenames in os.walk(pathname):
        for filename in filenames:
            files.append(os.sep.join([path, filename]))
    files.sort()
    sha1 = hashlib.sha1()
    for filename in files:
        if filename.endswith('.pyc'):
            continue
        try:
            with open(filename, 'rb') as fh:
                while 1:
                    buf = fh.read(1024*4)
                    if not buf:
                        break
                    sha1.update(buf)
        except IOError:
            logger.debug('could not open %s' % filename)
            pass
    return sha1.hexdigest()

def hashmodule(pathname):
    """Calculate the SHA1 sum of all relative imports in a script.

    It operates by going through all modules that ModuleFinder.run_script
    finds, sorting them alphabetically and calculating the SHA1 of
    the contents of the files.

    Parameters
    ----------
    pathname : str
        the path of the script to check

    Returns
    -------
    hexdigest : str
        the SHA1

    Examples
    --------

    >>> hashmodule('demo01_stopping.py')
    'd2c07aafb6fbf2474f3b38e3baf4bb931994d844'

    """
    logger.debug(f"Hashing module {pathname}")
    finder = ModuleFinder()
    finder.run_script(pathname)
    # finder.modules is a dict modulename:module
    # only keep relative modules
    paths = {name:Path(mod.__file__)
            for name, mod in finder.modules.items()
            if mod.__file__}
    relative_paths = [
        (name, p) for name, p in paths.items()
        if not p.is_absolute()
    ]
    # sort relative paths by module name and generate our sha
    sha1 = hashlib.sha1()
    for name, path in sorted(relative_paths):
        logger.debug(f"Hashing {pathname}: Adding {name}")
        sha1.update(path.read_bytes())
    res = sha1.hexdigest()
    logger.debug(f"SHA1 for {pathname}: {res}.")
    return res

class Test_DB_Wrapper(unittest.TestCase):
    """Tests for the DB_Wrapper class."""

    def setUp(self):
        self.wrapper = DB_Wrapper(':memory:')
        self.wrapper.create_tables()

    def test_foreign_keys_enabled(self):
        result = self.wrapper.cursor.execute("PRAGMA foreign_keys;").fetchone()
        self.assertEqual(result[0], 1)

    def test_add_player(self):
        self.wrapper.add_player('p1', 'h1')
        self.wrapper.add_player('p2', 'h2')
        with self.assertRaises(ValueError):
            self.wrapper.add_player('p1', 'h1')
        players = sorted(self.wrapper.get_players())
        self.assertEqual(players, ['p1', 'p2'])

    def test_remove_player(self):
        self.wrapper.add_player('p1', 'h1')
        self.wrapper.add_player('p2', 'h2')
        self.wrapper.add_player('p3', 'h3')
        self.wrapper.add_gameresult('p1', 'p2', 0, '', '')
        self.wrapper.add_gameresult('p2', 'p1', 0, '', '')
        self.wrapper.add_gameresult('p2', 'p3', 0, '', '')
        # player2 has three games
        self.assertEqual(len(self.wrapper.get_results('p2')), 3)
        self.wrapper.remove_player('p1')
        # player 1 should have no game results
        self.assertEqual(self.wrapper.get_results('p1'), [])
        # after removing all games of player one, player2 should have 1
        # game
        self.assertEqual(len(self.wrapper.get_results('p2')), 1)
        # player 3 should be untouched
        self.assertEqual(len(self.wrapper.get_results('p3')), 1)

    def test_add_remove_weirdly_named_player(self):
        stupid_names = [
            "Little'",
            'Bobby"',
            "таблицы",
        ]

        for name in stupid_names:
            self.wrapper.add_player(name, name)
            self.wrapper.remove_player(name)

    def test_get_players(self):
        players = ['p1', 'p2', 'p3']
        for p in players:
            self.wrapper.add_player(p, 'h')
        players2 = sorted(self.wrapper.get_players())
        self.assertEqual(players, players2)

    def test_get_results(self):
        self.wrapper.add_player('p1', 'h1')
        self.wrapper.add_player('p2', 'h2')
        # empty list if no results are available
        self.assertEqual(self.wrapper.get_results('p1'), [])
        self.wrapper.add_gameresult('p1', 'p2', 0, '', '')
        result = self.wrapper.get_results('p1')[0]
        # check for correct values
        self.assertEqual(result[0], 'p1')
        self.assertEqual(result[1], 'p2')
        self.assertEqual(result[2], 0)
        self.assertEqual(result[3], '')
        self.assertEqual(result[4], '')
        self.wrapper.add_gameresult('p2', 'p1', 0, '', '')
        # check for correct number of results
        results = self.wrapper.get_results('p1')
        self.assertEqual(len(results), 2)

    def test_get_player_hash(self):
        self.wrapper.add_player('p1', 'h1')
        self.wrapper.add_player('p2', 'h2')
        with self.assertRaises(ValueError):
            self.wrapper.get_player_hash('p0')
        self.assertEqual(self.wrapper.get_player_hash('p1'), 'h1')
        self.assertEqual(self.wrapper.get_player_hash('p2'), 'h2')


if __name__ == '__main__':
    if args.test:
        unittest.main(argv=sys.argv[:1], verbosity=2)
    else:
        ci_engine = CI_Engine()
        ci_engine.start(args.n)


