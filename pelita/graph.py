""" Basic graph module """

import heapq
from collections import deque


class NoPathException(Exception):
    pass

def move_pos(position, move):
    """ Adds a position tuple and a move tuple.

    Parameters
    ----------
    position : tuple of int (x, y)
        current position

    move : tuple of int (x, y)
        direction vector

    Returns
    -------
    move_pos : tuple of int (x, y)
        new position coordinates

    """
    pos_x = position[0] + move[0]
    pos_y = position[1] + move[1]
    return (pos_x, pos_y)

def diff_pos(initial, target):
    """ Return the move required to move from one position to another.

    Will return the move required to transition from `initial` to `target`. If
    `initial` equals `target` this is `stop`.

    Parameters
    ----------
    initial : tuple of (int, int)
        the starting position
    target : tuple of (int, int)
        the target position

    Returns
    -------
    move : tuple of (int, int)
        the resulting move

    """
    return (target[0]-initial[0], target[1]-initial[1])

def manhattan_dist(pos1, pos2):
    """ Manhattan distance between two points.

    Parameters
    ----------
    pos1 : tuple of (int, int)
        the first position
    pos2 : tuple of (int, int)
        the second position

    Returns
    -------
    manhattan_dist : int
        Manhattan distance between two points
    """
    return sum(abs(idx) for idx in diff_pos(pos1, pos2))

def iter_adjacencies(initial, adjacencies_for_pos):
    """ Returns an adjacency list starting at the initial positions.

    Given some starting positions and a method which returns the adjacencies
    per position, we iterate over all reachable positions and their respective
    neighbours.

    Parameters
    ----------
    initial : list(pos)
        List of initial positions
    adjacencies_from_pos : callable
        Given a position, this function should return all reachable positions.

    Returns
    -------
    adjacency_list : generator of (pos, list(pos))
        Generator which contains all reachable positions and their adjacencies
    """
    reached = set()
    todo = set(initial)
    while todo:
        pos = todo.pop()
        legal_moves = adjacencies_for_pos(pos)
        for move in legal_moves:
            if move not in reached:
                todo.add(move)
        reached.add(pos)
        yield (pos, legal_moves)

class AdjacencyList(dict):
    """ Adjacency list [1] representation of a Maze.

    The `AdjacencyList` is mostly a wrapper for a `dict`. Given a position,
    it returns the positions reachable from there.

    [1] http://en.wikipedia.org/wiki/Adjacency_list

    """
    def __init__(self, adjacencies):
        self.update(adjacencies)

    def pos_within(self, position, distance):
        """ Positions within a certain distance.

        Calculates all positions within a certain distance of a target
        `position` in maze space. Within means strictly less than (`<`) in this
        case.

        Parameters
        ----------
        position : tuple of (int, int)
            the first position

        distance : int
            the distance in maze space

        Returns
        -------
        pos_within : set of tuple of (int, int)
            the positions within the given distance

        Raises
        ------
        NoPathException
            if `position` does not exist in the adjacency list

        """
        self._check_pos_exist([position])
        positions = set([position])
        to_visit = [position]
        for i in range(distance):
            local_to_visit = []
            for pos in to_visit:
                if pos not in positions:
                    positions.add(pos)
                local_to_visit.extend(self[pos])
            to_visit = local_to_visit
        return positions

    def _check_pos_exist(self, positions):
        for pos in positions:
            if pos not in self.keys():
                raise NoPathException("Position %s does not exist in adjacency list." %
                        repr(pos))

    def bfs(self, initial, targets):
        """ Breadth first search (bfs).

        Breadth first search [1] from one position to multiple targets. The
        search will return a path from the `initial` position to the closest
        position in `targets`.

        Parameters
        ----------
        initial : tuple of (int, int)
            the first position
        targets : list of tuple of (int, int)
            the target positions

        Returns
        -------
        path : lits of tuple of (int, int)
            the path from `initial` to the closest `target`

        Raises
        ------
        NoPathException
            if no path from `initial` to one of `targets`
        NoPositionException
            if either `initial` or `targets` does not exist

        [1] http://en.wikipedia.org/wiki/Breadth-first_search

        """
        # First check that the arguments were valid.
        self._check_pos_exist([initial] + targets)
        # Initialise `to_visit` of type `deque` with current position.
        # We use a `deque` since we need to extend to the right
        # but pop from the left, i.e. its a fifo queue.
        to_visit = deque([initial])
        # `seen` is a list of nodes we have seen already
        # We append to right and later pop from right, so a list will do.
        # Order is important for the back-track later on, so don't use a set.
        seen = []
        found = False
        while to_visit:
            current = to_visit.popleft()
            if current in seen:
                # This node has been seen, ignore it.
                continue
            elif current in targets:
                # We found some food, break and back-track path.
                found = True
                break
            else:
                # Otherwise keep going, i.e. add adjacent nodes to seen list.
                seen.append(current)
                to_visit.extend(self[current])
        # if we did not find any of the targets, raise an Exception
        if not found:
            raise NoPathException("BFS: No path from %r to %r."
                    % (initial, targets))
        # Now back-track using seen to determine how we got here.
        # Initialise the path with current node, i.e. position of food.
        path = [current]
        while seen:
            # Pop the latest node in seen
            next_ = seen.pop()
            # If that's adjacent to the current node
            # it's in the path
            if next_ in self[current]:
                # So add it to the path
                path.append(next_)
                # And continue back-tracking from there
                current = next_
        # The last element is the current position, we don't need that in our
        # path, so don't include it.
        return path[:-1]

    def a_star(self, initial, target):
        # The set of nodes already evaluated.
        closed_set = set()
        # the set of currently discovered nodes still to be evaluated.
        # initially, only the start node is known.
        open_set = {initial}
        # for each node, which node it can most efficiently be reached from.
        # if a node can be reached from many nodes, cameFrom will eventually contain the
        # most efficient previous step.
        came_from = dict()

        # for each node, the cost of getting from the start node to that node.
        import collections
        import math
        g_score = collections.defaultdict(default_factory=lambda k: math.inf)
        # the cost of going from start to start is zero.
        g_score[initial]= 0

        # for each node, the total cost of getting from the start node to the goal
        # by passing by that node. That value is partly known, partly heuristic.
        f_score = collections.defaultdict(default_factory=lambda k: math.inf)
        # for the first node, that value is completely heuristic.
        f_score[initial] = manhattan_dist(initial, target)

        while open_set:
            current = sorted((f_score[node], node) for node in open_set)[0][1]# the node in openSet having the lowest fScore[] value
            if current == target:
                return reconstruct_path(came_from, current)[:-1]

            open_set.remove(current)
            closed_set.add(current)
            try:
                neighbors = self[current]
            except KeyError:
                raise NoPathException("A*: No path from %r to %r." % (initial, target))

            for neighbor in neighbors:
                if neighbor in closed_set:
                    continue           # Ignore the neighbor which is already evaluated.
                # the distance from start to a neighbor
                tentative_g_score = g_score[current] + 1
                if neighbor not in open_set:  # Discover a new node
                    open_set.add(neighbor)
                elif tentative_g_score >= g_score[neighbor]:
                    continue           # This is not a better path.

                # this path is the best until now. Record it!
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g_score
                f_score[neighbor] = g_score[neighbor] + manhattan_dist(neighbor, target)

        raise NoPathException("A*: No path from %r to %r." % (initial, target))

def reconstruct_path(came_from, current):
    total_path = [current]
    while current in came_from.keys():
        current = came_from[current]
        total_path.append(current)
    return total_path

