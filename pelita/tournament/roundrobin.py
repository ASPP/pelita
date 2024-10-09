from collections import Counter
import itertools
from typing import List, Tuple

def create_matchplan(teams: List[str], rng) -> List[Tuple[str, str]]:
    """ Takes a list of team ids and returns a list of tuples of team ids with
    the matchplan."""

    # We want to optimise the matchplan in multiple ways:
    # a) At any point each team should have a similar number of played games
    # b) No team should play two games directly after another;
    # both of these points should make the tournament more interesting to
    # follow.
    # Finally, in the interest of fairness:
    # c) Blue and red teams (ie. who starts the match) should be assigned evenly.
    #
    # For an even number of teams (> 4), these points can be fulfilled with the
    # circle method; for an odd number of teams, however, it should be noted
    # that the circle method is not the most optimal algorithm. [1]
    #
    # As having five teams is the usual case during ASPP student tournaments,
    # we will special-case this one and implement the circle method in all
    # other cases. (Arguably, round-robin tournaments with more than 6 teams
    # will tend to become rather lengthy and should probably be executed
    # differently anyway.)
    #
    # Further reading
    # [1]: Scheduling Asynchronous Round-Robin Tournaments, W. Suksompong, arXiv:1804.04504 [math.CO]


    if len(teams) == 3:
        matchplan_indexes = matchplan_three_teams(rng)
    elif len(teams) == 5:
        matchplan_indexes = matchplan_five_teams(rng)
    else:
        matchplan_indexes = circle_method(len(teams), rng)

    shuffled_teams = list(teams)
    rng.shuffle(shuffled_teams)

    matchplan = []
    for match in matchplan_indexes:
        idx_a, idx_b = match
        a = shuffled_teams[idx_a]
        b = shuffled_teams[idx_b]
        matchplan.append((a, b))

    return matchplan

def matchplan_three_teams(rng):
    # Without loss of generality, there should be exactly two possible matchplans with evenly distributed blue/red
    matchplans = [
        [(0, 1), (1, 2), (2, 0)],
        [(0, 1), (2, 0), (1, 2)]
    ]
    return rng.choice(matchplans)

def matchplan_five_teams(rng):
    # Without loss of generality, there are two possible matchplans for five teams (with the starting order undefined)
    # that don’t have the same team play two consecutive matches. (Assuming the teams are assigned randomly.)
    # (Source: pen&paper + brute force analysis)
    #
    # [{0, 1}, {2, 3}, {0, 4}, {1, 2}, {3, 4}, {0, 2}, {1, 3}, {2, 4}, {0, 3}, {1, 4}]
    # [{0, 1}, {2, 3}, {0, 4}, {1, 2}, {3, 4}, {0, 2}, {1, 4}, {0, 3}, {2, 4}, {1, 3}]

    matchplan = rng.choice([
        [(0, 1), (2, 3), (0, 4), (1, 2), (3, 4), (0, 2), (1, 3), (2, 4), (0, 3), (1, 4)],
        [(0, 1), (2, 3), (0, 4), (1, 2), (3, 4), (0, 2), (1, 4), (0, 3), (2, 4), (1, 3)]
    ])

    # collect all matchplans that have an equal distribution of blue/red matches
    # TODO: It should be possible to reduce the possible combinations for this in advance.
    valid_matchplans = []
    for shuffle in itertools.product([0, 1], repeat=len(matchplan)):
        # for each possible order, make a histogram of each team playing blue
        # as we have five teams, we know that each team should play blue exactly twice
        if set(Counter(match[idx] for match, idx in zip(matchplan, shuffle)).values()) == {2}:
            valid_mp = [(match[idx], match[1 - idx]) for match, idx in zip(matchplan, shuffle)]
            valid_matchplans.append(valid_mp)

    return rng.choice(valid_matchplans)

def circle_method(num_teams, rng):
    return list(circle_method_gen(num_teams, rng))

def circle_method_gen(num_teams, rng):
    """ For the given number of teams, create a matchplan for a round-robin tournament using the circle method. """

    FILLER_TEAM = object()

    teams = list(range(num_teams))

    # add a dummy team if we have an odd number of teams
    # the matches will later be discarded
    if len(teams) % 2 != 0:
        teams.append(FILLER_TEAM)

    # choose an index that we keep fixed (must be in first or last column)
    #
    # entries are aligned clockwise
    #
    #  +---+---+---+---+
    #  | 0 | 1 | 2 | 3 |
    #  +---+---+---+---+
    #  | 4 | 5 | 6 | 7 |
    #  +---+---+---+---+
    #
    #  keep 0 fixed and rotate
    #
    #  +---+---+---+---+
    #  | 0 | 2 | 3 | 4 |
    #  +---+---+---+---+
    #  | 5 | 6 | 7 | 1 |
    #  +---+---+---+---+
    #
    # This gives us the starting matches: 04, 14, 26, 37, 50, 26, 37, 41, ...
    # Note that all matches of the fixed team need to be reversed in every second round

    # corner indexes
    if num_teams % 2 == 0:
        fixed_index = rng.choice([0, len(teams) // 2 - 1, len(teams) // 2, len(teams) - 1])
    else:
        # for an odd number of teams, only select the column with the filler team
        fixed_index = rng.choice([0, len(teams) - 1])

    flip_fixed = False
    for _iter in range(len(teams) - 1):
        teams = rotate_with_fixed(teams, fixed_index)

        # pair the matches
        for match_idx in range(len(teams) // 2):
            # pair a team from the top of the list with a team from the bottom
            top_index = match_idx
            bottom_index = len(teams) - match_idx - 1
            match = teams[top_index], teams[bottom_index]

            # the pairing with the fixed team needs to be flipped every other time
            if fixed_index in [top_index, bottom_index]:
                if flip_fixed:
                    match = teams[bottom_index], teams[top_index]
                flip_fixed = not flip_fixed

            if FILLER_TEAM in match:
                continue
            yield match

def rotate_with_fixed(lst: List, index: int) -> List:
    lst = list(lst)

    # remove index
    removed_team = lst.pop(index)
    # rotate
    lst = lst[1:] + lst[:1]
    # insert again
    lst.insert(index, removed_team)
    return lst
