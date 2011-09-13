#!/usr/bin/env python

# TODO: add fancier logging maybe w/ colored output

from subprocess import Popen, PIPE


# Number of points a teams gets for matches in the first round
POINTS_DRAW = 1
POINTS_WIN = 2

# FIXME: fit that for tournatment
CMD_STUB = 'python ../pelitagame --rounds=100 --null'

# the 'real' names of the teams (instead of group0 .. group4). they are
# collected while the tournament goes
rnames = {'group0' : 'group0',
          'group1' : 'group1',
          'group2' : 'group2',
          'group3' : 'group3',
          'group4' : 'group4' }


def organize_first_round(nr_teams):
    """Return the order of matches in round one.

    In the first round each team plays against all other teams exactly once.
    """
    return [[i, j] for i in range(nr_teams) for j in range(i+1, nr_teams)]


def start_match(team1, team2):
    """Start a match between team1 and team2. Return which team won (1 or 2) or
    0 if there was a draw.
    """
    global rnames
    print
    print rnames[team1], 'vs', rnames[team2]
    print
    args = CMD_STUB.split()
    args.extend([team1, team2])
    print 'Starting', ' '.join(args)
    stdout, stderr = Popen(args, stdout=PIPE, stderr=PIPE).communicate()
    tmp = reversed(stdout.splitlines())
    lastline = None
    # get the real names of the teams.
    # pelitagame will output two lines of the following form:
    # Using factory 'RandomPlayer' -> 'The RandomPlayers'
    for line in stdout.splitlines():
        if line.startswith("Using factory '"):
            split = line.split("'")
            tname, rname = split[1], split[3]
            rnames[tname] = rname
    for line in tmp:
        if line.startswith('Finished.'):
            lastline = line
            break
    if not lastline:
        print "*** ERROR: Aparently the game crashed. At least I could not find the outcome of the game."
        print "*** Maybe stderr helps you to debug the problem"
        print stderr
        print "***"
        return 0
    print "***", lastline
    if lastline.find('had a draw.') >= 0:
        print "Draw!"
        return 0
    else:
        tmp = lastline.split("'")
        winner = tmp[1]
        loser = tmp[3]
        if winner == rnames[team1]:
            print team1, 'wins.'
            return 1
        elif winner == rnames[team2]:
            print team2, 'wins.'
            return 2
        else:
            print "Unable to parse winning result :("
            return 0


def start_deathmatch(team1, team2):
    """Start a match between team1 and team2 until one of them wins (ie no
    draw.)
    """
    while True:
        r = start_match(team1, team2)
        if r == 0:
            print 'Draw -> Deathmatch!'
            continue
        winner = team1 if r == 1 else team2
        return winner


def pp_round1_results(teams, points):
    """Pretty print the current result of the matches."""
    global rnames
    result = sorted(zip(points, teams), reverse=True)
    print
    for p, t in result:
        print "  %25s %d" % (rnames[t], p)
    print

def round1(teams):
    """Run the first round and return a sorted list of team names."""
    print
    print "ROUND 1 (Everybody vs Everybody)"
    print '================================'
    print
    points = [0 for i in range(len(teams))]
    round1 = organize_first_round(len(teams))
    for t1, t2 in round1:
        winner = start_match(teams[t1], teams[t2])
        if winner == 0:
            points[t1] += POINTS_DRAW
            points[t2] += POINTS_DRAW
        else:
            points[[t1, t2][winner-1]] += POINTS_WIN
        pp_round1_results(teams, points)
    print "Results of the first round."
    pp_round1_results(teams, points)
    # Sort the teams by points and return the team names as a list
    result = sorted(zip(points, teams), reverse=True)
    result = [t for p, t in result]
    return result


def pp_round2_results(teams, w1, w2, w3, w4):
    """Pretty print the results for the K.O. round."""
    global rnames
    feed = 10
    print
    print rnames[teams[0]]
    print " "*feed, rnames[w1]
    print rnames[teams[3]]
    print
    print " "*2*feed, rnames[w3]
    print
    print rnames[teams[1]]
    print " "*feed, rnames[w2]
    print rnames[teams[2]]
    print
    print " "*3*feed, rnames[w4]
    print
    print rnames[teams[4]]
    print


def round2(teams):
    """Run the second round and return the name of the winning team."""
    print
    print 'ROUND 2 (K.O.)'
    print '=============='
    print
    w1, w2, w3, w4 = "???", "???", "???", "???"
    # 1 vs 4
    w1 = start_deathmatch(teams[0], teams[3])
    pp_round2_results(teams, w1, w2, w3, w4)
    # 2 vs 3
    w2 = start_deathmatch(teams[1], teams[2])
    pp_round2_results(teams, w1, w2, w3, w4)
    # w1 vs w2
    w3 = start_deathmatch(w1, w2)
    pp_round2_results(teams, w1, w2, w3, w4)
    # W vs team5
    w4 = start_deathmatch(w3, teams[4])
    pp_round2_results(teams, w1, w2, w3, w4)
    return w4


if __name__ == '__main__':
    teams = ['group0', 'group1', 'group2', 'group3', 'group4']
    result = round1(teams)
    winner = round2(result)

