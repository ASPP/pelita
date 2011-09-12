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
    # TODO: start the actual match
    return 1


if __name__ == '__main__':
    teams = get_teams()
    # round 1
    points1 = [0 for i in range(len(teams))]
    round1 = organize_first_round(len(teams))
    print "ROUND 1 (Everybody vs Everybody)"
    for t1, t2 in round1:
        print teams[t1], 'vs', teams[t2],
        winner = start_match(teams[t1], teams[t2])
        if winner == 0:
            print 'draw.'
            points1[t1] += POINTS_DRAW
            points1[t2] += POINTS_DRAW
        else:
            print [teams[t1], teams[t2]][winner-1], 'won.'
            points1[[t1, t2][winner-1]] += POINTS_WIN
    print "Results of the first round."
    print sorted(zip(points1, teams), reverse=True)

