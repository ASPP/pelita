#!/usr/bin/env python

# Copyright (C) 2013 Bastian Venthur

# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


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


from __future__ import division

import ConfigParser
import hashlib
import logging
import os
import random
import sqlite3
import subprocess


logging.basicConfig(format='%(relativeCreated)10.0f %(levelname)8s %(message)s', level=logging.NOTSET)
logger = logging.getLogger(__name__)
logger.info('Logger started')

# the path of the configuration file
CFG_FILE = './ci.cfg'


class CI_Engine(object):
    """Continuous Integration Engine.


    """

    def __init__(self, cfgfile=CFG_FILE):
        self.players = []
        config = ConfigParser.ConfigParser()
        config.read(os.path.abspath(cfgfile))
        for name, path in  config.items('agents'):
            if os.path.isdir(path):
                self.players.append({'name' : name,
                                     'path' : path
                                     })
            else:
                logger.warning('%s seems not to be an existing directory, ignoring %s' % (path, name))
        self.pelita_exe = config.get('general', 'pelita_exe')
        self.default_args = config.get('general', 'default_args').split()
        self.db_file = config.get('general', 'db_file')
        self.dbwrapper = DB_Wrapper(self.db_file)
        # remove players from db which are not in the config anymore
        for pname in self.dbwrapper.get_players():
            if pname not in [p['name'] for p in self.players]:
                logger.debug('Removing %s from data base, because he is not among the current players.' % (pname))
                self.dbwrapper.remove_player(pname)
        # add new players into db
        for pname, path in [[p['name'], p['path']] for p in self.players]:
            if pname not in self.dbwrapper.get_players():
                logger.debug('Adding %s to data base.' % pname)
                self.dbwrapper.add_player(pname, hashdir(path))
        # reset players where the directory hash changed
        for player in self.players:
            path = player['path']
            name = player['name']
            if hashdir(path) != self.dbwrapper.get_player_hash(name):
                logger.debug('Resetting %s because his directory hash changed.' % name)
                self.dbwrapper.remove_player(name)
                self.dbwrapper.add_player(name, hashdir(path))


    def run_game(self, p1, p2):
        """Run a single game.

        This method runs a single game ``p1`` vs ``p2`` and internally
        stores the result.

        Parameters
        ----------
        p1, p2 : int
            the indices of the players

        """
        left, right = [self.players[i]['path'] for i in p1, p2]
        proc_args = [self.pelita_exe, left, right]
        proc_args.extend(self.default_args)

        proc = subprocess.Popen(proc_args,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        std_out, std_err = proc.communicate()
        last_line = std_out.strip().splitlines()[-1]
        try:
            result = -1 if last_line == '-' else int(last_line)
        except ValueError:
            logger.error("Couldn't parse the outcome of the game:")
            logger.error("STDERR: \n%s" % std_err)
            logger.error("STDOUT: \n%s" % std_out)
            logger.error("Ignoring the result.")
            return
        p1_name, p2_name = self.players[p1]['name'], self.players[p2]['name']
        self.dbwrapper.add_gameresult(p1_name, p2_name, result, std_out, std_err)


    def start(self):
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
        while 1:
            # choose the player with the least number of played game,
            # mix him with another random player
            # mis the sides and let them play
            game_count = [[sum(self.get_results(i)), i] for i in range(len(self.players))]
            players_sorted = [idx for count, idx in sorted(game_count)]
            a, rest = players_sorted[0], players_sorted[1:]
            b = random.choice(rest)
            players = [a, b]
            random.shuffle(players)
            self.run_game(players[0], players[1])
            self.pretty_print_results()
            print '------------------------------'


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
        print '                                       ' + ''.join("%14s" % p['name'] for p in self.players)
        result = []
        for idx, p in enumerate(self.players):
            win, loss, draw = self.get_results(idx)
            score = 0 if (win+loss+draw) == 0 else (win-loss) / (win+loss+draw)
            result.append([score, p['name']])
            print '%13s (%6.2f): %3d,%3d,%3d\t' % (p['name'], score, win, loss, draw),
            for idx2, p2 in enumerate(self.players):
                win, loss, draw = self.get_results(idx, idx2)
                print '  %3d,%3d,%3d' % (win, loss, draw),
            print
        print
        result.sort(reverse=True)
        for [score, name] in result:
            print "%15s %6.2f" % (name, score)


class DB_Wrapper(object):
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
        WHERE name = '%s'
        """ % name).fetchone()
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
        WHERE player1 = '%s' or player2 = '%s'""" % (pname, pname))
        self.cursor.execute("""DELETE FROM players
        WHERE name = '%s'""" % pname)
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
            WHERE player1 = '%s' or player2 = '%s'""" % (p1_name, p1_name))
            relevant_results = self.cursor.fetchall()
        else:
            self.cursor.execute("""
            SELECT * FROM games
            WHERE (player1 = '%s' and player2 = '%s') or (player1 = '%s' and player2 = '%s')""" % (p1_name, p2_name, p2_name, p1_name))
            relevant_results = self.cursor.fetchall()
        return relevant_results


def hashdir(pathname):
    """Calculate the SHA1 sum of the contents of a directory.

    It operates by walking trough the directory, collecting all
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
        try:
            with open(filename) as fh:
                while 1:
                    buf = fh.read(1024*4)
                    if not buf:
                        break
                    sha1.update(buf)
        except IOError:
            logger.debug('could not open %s' % filename)
            pass
    return sha1.hexdigest()


if __name__ == '__main__':
    ci_engine = CI_Engine()
    ci_engine.start()


