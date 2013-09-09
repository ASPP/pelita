#!/usr/bin/env python

# Copyright (C) 2013 Bastian Venthur

# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:


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
import random
import subprocess
import os


# the path of the configuration file
CFG_FILE = './ci.cfg'


class CI_Engine(object):
    """Continuous Integration Engine.


    """

    def __init__(self):
        self.players = []
        # array of [p1, p2, result, std_out, std_err]
        self.results = []

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
            print "*** Couldn't parse the outcome of the game:"
            print "*** STDERR:"
            print std_err
            print "*** STDOUT:"
            print std_out
            # just ignore this game
            return
        self.results.append([p1, p2, result, std_out, std_err])


    def configure(self, cfgfile=CFG_FILE):
        """Configure the CI Engine.

        This method reads the configuration file and configures itself.
        It is mainly used to read in the agents.

        Parameters
        ----------
        cfgfile : str, optional
            path to the configuration file, the default is './ci.cfg'

        """
        config = ConfigParser.ConfigParser()
        config.read(os.path.abspath(cfgfile))
        for name, path in  config.items('agents'):
            if os.path.isdir(path):
                self.players.append({'name' : name,
                                     'path' : path
                                     })
            else:
                print '%s seems not to be an existing directory, ignoring %s' % (path, name)
        self.pelita_exe = config.get('general', 'pelita_exe')
        self.default_args = config.get('general', 'default_args').split()


    def start(self):
        """Start the Engine.

        This method will start and infinite loop, testing each agent
        randomly against another one. The result is printed after each
        game.

        Currently the only way to stop the engine is via CTRL-C.

        Examples
        --------
        >>> ci = CI_Engine()
        >>> ci.configure()
        >>> ci.start()

        """
        while 1:
            players = range(len(self.players))
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
        for p1, p2, r, std_out, std_err in self.results:
            if (idx2 is None and idx == p1) or (idx2 is not None and idx == p1 and idx2 == p2):
                if r == 0: win += 1
                elif r == 1: loss += 1
                elif r == -1: draw += 1
                else: print 'purrrr!'
            if (idx2 is None and idx == p2) or (idx2 is not None and idx == p2 and idx2 == p1):
                if r == 1: win += 1
                elif r == 0: loss += 1
                elif r == -1: draw += 1
                else: print 'purrrr!'
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


if __name__ == '__main__':
    ci_engine = CI_Engine()
    ci_engine.configure()
    ci_engine.start()


