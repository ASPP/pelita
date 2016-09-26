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


    def a_star_search(self, start, goal):
        frontier = PriorityQueue()
        frontier.put(start, 0)
        came_from = {}
        cost_so_far = {}
        came_from[start] = None
        cost_so_far[start] = 0

        while not frontier.empty():
            current = frontier.get()

            if current == goal:
                break

            for next in self[current]:
                new_cost = cost_so_far[current] + 1
                if next not in cost_so_far or new_cost < cost_so_far[next]:
                    cost_so_far[next] = new_cost
                    priority = new_cost + manhattan_dist(goal, next)
                    frontier.put(next, priority)
                    came_from[next] = current

        return came_from, cost_so_far

    def a_star(self, start, goal):
        try:
            came_from, cost = self.a_star_search(start, goal)
            return reconstruct_path(came_from, start, goal)[:-1]
        except KeyError:
            raise NoPathException("")

class PriorityQueue:
    def __init__(self):
        self.elements = []

    def empty(self):
        return len(self.elements) == 0

    def put(self, item, priority):
        heapq.heappush(self.elements, (priority, item))

    def get(self):
        return heapq.heappop(self.elements)[1]

def reconstruct_path(came_from, start, goal):
    current = goal
    path = [current]
    while current != start:
        current = came_from[current]
        path.append(current)
    path.reverse() # optional
    return path

