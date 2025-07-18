import math
import queue
from collections import defaultdict, namedtuple
from io import StringIO


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


def build_bracket(teams):
    """
    Build a match tree from the given list of teams.

    Given a ranking in teams, we want to ensure that the best teams
    only play against each other in the last possible moment.

    Examples:

        1 ──┐
            ├─
        2 ┐ │
          ├─┘
        3 ┘

        1 ┐
          ├─┐
        4 ┘ │
            ├─
        2 ┐ │
          ├─┘
        3 ┘

        1 ──┐
            ├─┐
        4 ┐ │ │
          ├─┘ │
        5 ┘   ├─
              │
        2 ──┐ │
            ├─┘
        3 ──┘

    Note that this is the situation without a bonus match. The team that is selected for the
    bonus round, will be removed from the list before building the match tree and then added
    in a final step, leading to a pattern like:

        1 ┐
          ├─┐
        4 ┘ │
            ├─┐
        2 ┐ │ │
          ├─┘ ├─
        3 ┘   │
              │
        5 ────┘


    There is a formula in https://oeis.org/A131271 but the recursive method
    may be simpler to follow: For each four teams we reserve the first and the last team
    in a list for the top bracket; places two and three in a list for the bottom bracket.
    We then apply the algorithm recursively to the top and bottom bracket.
    """
    if len(teams) == 1:
        return teams[0]

    # fill missing teams so we have a power of 2 positions
    depth = int(math.log2(len(teams)))
    fill = len(teams) - 2**depth
    teams = teams + fill * [None]

    # recursively match first against fourth, second against third
    top_bracket = []
    bottom_bracket = []
    for idx, team in enumerate(teams):
        match idx % 4:
            case 0|3:
                top_bracket.append(team)
            case _:
                bottom_bracket.append(team)
    return [build_bracket(top_bracket), build_bracket(bottom_bracket)]

def build_match_tree(bracket):
    match bracket:
        case [t1, None]:
            return Bye(team=build_match_tree(t1))
        case [None, t2]:
            # build_bracket should not create this pattern
            # but we catch it anyway
            return Bye(team=build_match_tree(t2))
        case [t1, t2]:
            return Match(t1=build_match_tree(t1), t2=build_match_tree(t2))
        case name:
            return Team(name=name)


def prepare_matches(teams, bonusmatch=False):
    """ Takes a ranked list of teams and returns the Match tree.
    """

    if not teams:
        raise ValueError("No teams given to sort.")

    if bonusmatch:
        bonus_team = teams.pop()
        if not teams:
            # seems we have a winner
            return Team(bonus_team)

    bracket = build_bracket(teams)
    match_tree = build_match_tree(bracket)

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
    match tree:
        case Match(t1, t2):
            # subtrees must have the same maximum depth
            # and be balanced at all spots
            return (is_balanced(t1) and is_balanced(t2)
                    and tree_depth(t1) == tree_depth(t2))
        case Bye(_) | Team(_):
           return True

def tree_depth(tree):
    match tree:
        case Match(t1, t2):
            return 1 + max(tree_depth(t1), tree_depth(t2))
        case Bye(team):
            return 1 + tree_depth(team)
        case Team(_):
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
