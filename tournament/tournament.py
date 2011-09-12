#!/usr/bin/env python


# Number of points a teams gets for matches in the first round
POINTS_DRAW = 1
POINTS_WIN = 2


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
    return 1


def start_deathmatch(team1, team2):
    """Start a match between team1 and team2 until one of them wins (ie no
    draw.)
    """
    while True:
        r = start_match(team1, team2)
        if r == 0:
            continue
        return r


def round1(teams):
    points = [0 for i in range(len(teams))]
    round1 = organize_first_round(len(teams))
    print "ROUND 1 (Everybody vs Everybody)"
    for t1, t2 in round1:
        print teams[t1], 'vs', teams[t2],
        winner = start_match(teams[t1], teams[t2])
        if winner == 0:
            print 'draw.'
            points[t1] += POINTS_DRAW
            points[t2] += POINTS_DRAW
        else:
            print [teams[t1], teams[t2]][winner-1], 'won.'
            points[[t1, t2][winner-1]] += POINTS_WIN
    print "Results of the first round."
    print sorted(zip(points, teams), reverse=True)
    return zip(teams, points)


def round2(team1, team2, team3, team4, team5):
    # 1 vs 4
    r = start_deathmatch(team1, team4)
    w1 = team1 if r == 1 else team2
    # 2 vs 3
    r = start_deathmatch(team2, team3)
    w2 = team2 if r == 1 else team3
    # w1 vs w2
    r = start_deathmatch(w1, w2)
    w = w1 if r == 1 else w2
    # W vs team5
    r = start_deathmatch(w, team5)
    w = w if r == 1 else team5


if __name__ == '__main__':
    teams = get_teams()
    result = round1(teams)
    print result
    result = round2(teams)

