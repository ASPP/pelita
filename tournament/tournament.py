#!/usr/bin/env python


from subprocess import Popen, PIPE


# Number of points a teams gets for matches in the first round
POINTS_DRAW = 1
POINTS_WIN = 2

CMD_STUB = 'python pelitagame.py --rounds=10'

def get_teams():
    """Read participants.txt and return a list with the team names."""
    result = []
    with open('participants.txt', 'r') as fh:
        for line in fh.readlines():
            line = line.strip()
            if line.startswith('#') or len(line) == 0:
                continue
            result.append(line)
    return result


def organize_first_round(nr_teams):
    """Return the order of matches in round one.

    In the first round each team plays against all other teams exactly once.
    """
    return [[i, j] for i in range(nr_teams) for j in range(i+1, nr_teams)]


def start_match(team1, team2):
    """Start a match between team1 and team2. Return which team won (1 or 2) or
    0 if there was a draw.
    """
    # TODO: start the actual match, parse the outcome and return 0, 1 or 2
    args = CMD_STUB.split()
    args.extend([team1, team2])
    p = Popen(args, cwd='..', stdout=PIPE, stderr=PIPE)
    out = p.stdout.read()
    err = p.stderr.read()
    exitstatus = p.wait()
    print "exitstatus"
    print exitstatus
    print "stdout"
    print out
    print "stderr"
    print err
    print team1, 'vs', team2, '...'
    print team1, 'wins.'
    return 1


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


def round1(teams):
    points = [0 for i in range(len(teams))]
    round1 = organize_first_round(len(teams))
    print "ROUND 1 (Everybody vs Everybody)"
    for t1, t2 in round1:
        winner = start_match(teams[t1], teams[t2])
        if winner == 0:
            points[t1] += POINTS_DRAW
            points[t2] += POINTS_DRAW
        else:
            points[[t1, t2][winner-1]] += POINTS_WIN
    print "Results of the first round."
    result = sorted(zip(points, teams), reverse=True)
    print result
    result = [t for p, t in result]
    return result


def round2(teams):
    print 'ROUND 2 (K.O.)'
    # 1 vs 4
    w1 = start_deathmatch(teams[0], teams[3])
    # 2 vs 3
    w2 = start_deathmatch(teams[1], teams[2])
    # w1 vs w2
    w = start_deathmatch(w1, w2)
    # W vs team5
    w = start_deathmatch(w, teams[4])


if __name__ == '__main__':
    teams = get_teams()
    result = round1(teams)
    winner = round2(result)

