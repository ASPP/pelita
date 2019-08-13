import itertools
import math
import queue
from collections import defaultdict, namedtuple
from io import StringIO


def sort_ranks(teams, bonusmatch=False):
    """ Re-orders a ranked list of teams such that
    the best and worst team are next to each other,
    the second best and second best are next to each other, etc.

    If bonusmatch is True, then the worst team will be left
    out until the final match

    Parameters
    ----------
    teams : ranked list of teams

    Raises
    ------
    TypeError
        if new_data is not a list
    ValueError
        if new_data has inappropriate length

    """
    if len(teams) < 2:
        return teams

    if bonusmatch:
        # pop last item from teams list
        bonus_team = [teams.pop()]
    else:
        bonus_team = []

    # if the number of teams is not even, we need to leave out another team
    l = len(teams)
    if l % 2 != 0:
        # pop last item from teams list
        remainder_team = [teams.pop()]
    else:
        remainder_team = []

    # top half
    good_teams = teams[:l//2]
    # bottom half
    bad_teams = reversed(teams[l//2:2*(l//2)])

    pairs = [team for pair in zip(good_teams, bad_teams)
                  for team in pair]
    return pairs + remainder_team + bonus_team

def identity(x):
    return x

class MatrixElem:
    def size(self, trafo=identity):
        return len(self.to_s(trafo=trafo))

    def box(self, team, *, prefix=None, postfix=None, size=None, padLeft="", padRight="", fillElem="─", highlighted=False):
        if prefix is None:
            prefix = ""
        if postfix is None:
            postfix = ""

        if size is None:
            size = 0
        else:
            size = size - len(prefix) - len(postfix)

        BOLD = '\033[1m'
        END = '\033[0m'

        padded = "{padLeft}{team}{padRight}".format(team=team, padLeft=padLeft, padRight=padRight)
        return "{prefix}{BOLD}{team:{fillElem}<{size}}{END}{postfix}".format(team=padded, prefix=prefix, postfix=postfix,
                                                                             size=size, fillElem=fillElem,
                                                                             BOLD=BOLD if highlighted else "",
                                                                             END=END if highlighted else "")

class Team(namedtuple("Team", ["name"]), MatrixElem):
    def to_s(self, size=None, trafo=identity, highlighted=False):
        return self.box(trafo(self.name), size=size, prefix="", padLeft=" ", padRight=" ", highlighted=highlighted)

class Bye(namedtuple("Bye", ["team"]), MatrixElem):
    def to_s(self, size=None, trafo=identity, highlighted=False):
        prefix = "──"
        # return show_team("…", prefix=prefix, padLeft=" ", padRight=" ", size=size)
        return self.box("", size=size)

class Match(namedtuple("Match", ["t1", "t2"]), MatrixElem):
    def __init__(self, *args, **kwargs):
        self.winner = None

    def __repr__(self):
        return "Match(t1={}, t2={}, winner={})".format(self.t1, self.t2, self.winner)

    def to_s(self, size=None, trafo=identity, highlighted=False):
        prefix = "├─"
        name = trafo(self.winner) if (self.winner is not None) else "???"
        return self.box(name, prefix=prefix, padLeft=" ", padRight=" ", size=size, highlighted=highlighted)

class FinalMatch(namedtuple("FinalMatch", ["t1", "t2"]), MatrixElem):
    def __init__(self, *args, **kwargs):
        self.winner = None
    def to_s(self, size=None, trafo=identity, highlighted=False):
        prefix = "├──┨"
        postfix = "┃"
        fillElem = " "
        name = trafo(self.winner) if (self.winner is not None) else "???"
        return self.box(name, prefix=prefix, postfix=postfix, padLeft=" ", padRight=" ", fillElem=fillElem, size=size, highlighted=highlighted)

class Element(namedtuple("Element", ["char"]), MatrixElem):
    def to_s(self, size=None, trafo=identity, highlighted=False):
        return self.box(self.char, size=size, fillElem=" ", highlighted=highlighted)

class Empty(namedtuple("Empty", []), MatrixElem):
    def to_s(self, size=None, trafo=identity, highlighted=False):
        return self.box(" ", size=size, fillElem=" ")

class BorderTop(namedtuple("BorderTop", ["team", "tight"]), MatrixElem):
    def to_s(self, size=None, trafo=identity, highlighted=False):
        prefix = "│  " if not self.tight else "┐  "
        padRight = ""
        padLeft = "┏"
        postfix = "┓"
        fillElem = "━"
        return self.box("", prefix=prefix, postfix=postfix, padLeft=padLeft, padRight=padRight, fillElem=fillElem, size=size)

class BorderBottom(namedtuple("BorderBottom", ["team", "tight"]), MatrixElem):
    def to_s(self, size=None, trafo=identity, highlighted=False):
        prefix = "│  " if not self.tight else "┘  "
        padRight = ""
        padLeft = "┗"
        postfix = "┛"
        fillElem = "━"
        return self.box("", prefix=prefix, postfix=postfix, padLeft=padLeft, padRight=padRight, fillElem=fillElem, size=size)

def knockout_matrix(tree):
    """
    For now teams is a list (cols) of list (rows) of teams
    """
    teams = tree_enumerate(tree)

    initial_teams = teams[0]
    N = len(initial_teams)
    height = N * 2 - 1
    width = len(teams)

    matrix = [[Empty() for _w in range(width)] for _h in range(height)]
    # fill left column with initial teams
    for idx, t in enumerate(initial_teams):
        matrix[idx * 2][0] = t

    last_match = None

    for g_idx, generation in enumerate(teams):
        # print("G:", generation)
        if g_idx == 0:
            continue
        col = g_idx
        left_col = g_idx - 1
        for m_idx, match in enumerate(generation):
        #    print("M:", match)
            if isinstance(match, Match):
                # find row idx of the match partners
                for row_idx, row in enumerate(matrix):
                    if row[left_col] == match.t1:
                        start_row = row_idx
                    if row[left_col] == match.t2:
                        end_row = row_idx
                middle_row = math.floor(start_row + (end_row - start_row) / 2)

                # draw next match
                for row in range(start_row, end_row):
                    matrix[row][col] = Element('│')
                matrix[start_row][col] = Element('┐')
                matrix[end_row][col] = Element('┘')
                matrix[middle_row][col] = match
                last_match = (middle_row, col)

            if isinstance(match, Bye):
                for row_idx, row in enumerate(matrix):
                    if row[left_col] == match.team:
                        break
                matrix[row_idx][col] = match

    return matrix, last_match

def print_knockout(tree, name_trafo=identity, highlight=None):
    if highlight is None:
        highlight = []

    matrix, final_match = knockout_matrix(tree)

    winner_row = final_match[0]
    winning_team = matrix[final_match[0]][final_match[1]].winner
    winner = matrix[final_match[0]][final_match[1]] = FinalMatch(* matrix[final_match[0]][final_match[1]])
    winner.winner = winning_team

    def is_tight(elem):
        return not isinstance(elem, Empty) and not isinstance(elem, Element)

    matrix[winner_row - 1][-1] = BorderTop(winner, is_tight(matrix[winner_row - 1][-2]))
    matrix[winner_row + 1][-1] = BorderBottom(winner, is_tight(matrix[winner_row + 1][-2]))

    # estimate the width that a column needs
    colwidths = [0] * len(matrix[0])
    for row in matrix:
        for col_idx, elem in enumerate(row):
            current_width = elem.size(trafo=name_trafo)
            old_width = colwidths[col_idx]
            colwidths[col_idx] = max(current_width, old_width)

    with StringIO() as output:
        for row in range(len(matrix)):
            for col in range(len(matrix[0])):
                try:
                    elem = matrix[row][col]

                    str = elem.to_s(colwidths[col], trafo=name_trafo, highlighted=elem in highlight)
                    print(str, end="", file=output)
                except AttributeError:
                    print("Here:", end="")
                    print(row, col, matrix[row][col])
                    raise
            print(file=output)
        return output.getvalue()


def makepairs(matches):
    if len(matches) == 0:
        raise ValueError("Cannot prepare matches (no teams given).")
    while not len(matches) == 1:
        m = []
        pairs = itertools.zip_longest(matches[::2], matches[1::2])
        for p1, p2 in pairs:
            if p2 is not None:
                m.append(Match(p1, p2)) #  winner=None))
            else:
                m.append(Bye(p1))
        matches = m
    return matches[0]

def prepare_matches(teams, bonusmatch=False):
    """ Takes a ranked list of teams, matches them according to sort_ranks
    and returns the Match tree.
    """

    if not teams:
        raise ValueError("No teams given to sort.")

    teams_sorted = sort_ranks(teams, bonusmatch=bonusmatch)

    # If there is a bonus match, we must ensure that it will be played
    # at the very last
    if bonusmatch:
        bonus_team = teams_sorted.pop()
        if not teams_sorted:
            return Team(bonus_team)

    # pair up the games and return the tree starting from the winning team
    match_tree = makepairs([Team(t) for t in teams_sorted])

    if bonusmatch:
        # now add enough Byes to the bonus_team
        # so that we still have a balanced tree
        # when we add the bonus_team as a final match
        team = Team(bonus_team)
        for _depth in range(tree_depth(match_tree) - 1):
            team = Bye(team)

        match_tree = Match(match_tree, team)

    # ensure we have a balanced tree
    assert is_balanced(match_tree)

    return match_tree

def is_balanced(tree):
    if isinstance(tree, Match):
        return is_balanced(tree.t1) and is_balanced(tree.t2) and tree_depth(tree.t1) == tree_depth(tree.t2)
    if isinstance(tree, Bye):
        return True
    if isinstance(tree, Team):
        return True

def tree_depth(tree):
    if isinstance(tree, Match):
        return 1 + max(tree_depth(tree.t1), tree_depth(tree.t2))
    if isinstance(tree, Bye):
        return 1 + tree_depth(tree.team)
    if isinstance(tree, Team):
        return 1

def tree_enumerate(tree):
    enumerated = defaultdict(list)

    nodes = queue.Queue()
    nodes.put((tree, 0))
    while not nodes.empty():
        node, generation = nodes.get()
        if isinstance(node, Match):
            nodes.put((node.t1, generation + 1))
            nodes.put((node.t2, generation + 1))
        if isinstance(node, Bye):
            nodes.put((node.team, generation + 1))
        if isinstance(node, Team):
            pass
        enumerated[generation].append(node)

    generations = []
    for idx in sorted(enumerated.keys()):
        generations.append(enumerated[idx])
    generations.reverse()
    return generations
