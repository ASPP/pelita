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
    return abs(pos1[0]-pos2[0]) + abs(pos1[1]-pos2[1])

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

class Graph(dict):
    """ Adjacency list [1] representation of a Maze.

    The `Graph` is mostly a wrapper for a `dict`. Given a position,
    it returns the positions reachable from there.

    [1] http://en.wikipedia.org/wiki/Adjacency_list

    """
    def __init__(self, *args):
        if len(args) == 1:
            adjacencies = args[0]
            self.update(adjacencies)
            return

        initial, maze = args
        def legal_neighbors(maze, pos):
            neighbor_moves = [(-1, 0), (1, 0), (0, 1), (0, -1)]
            legal = []
            for move in neighbor_moves:
                neighbor = move_pos(pos, move)
                if not maze[neighbor]:
                    # this is not a wall
                    legal.append(neighbor)
            return legal

        self.update(it for it in iter_adjacencies([initial], lambda pos: legal_neighbors(maze, pos)))
        

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
        """ A* search.

        A* (A Star) [1] from one position to another. The search will return the
        shortest path from the `initial` position to the `target` using the
        Manhattan distance as a heuristic.
        Algorithm here is partially taken from [2] and inlined for speed.

        Parameters
        ----------
        initial : (int, int)
            the initial position
        target : (int, int)
            the target position

        Returns
        -------
        path : list of (int, int)
            one of the the shortest paths from `initial` to the closest `target`
            (excluding the `initial` position itself)

        Raises
        ------
        NoPathException
            if no path from `initial` to one of `targets`

        [1] http://en.wikipedia.org/wiki/A*_search_algorithm
        [2] http://www.redblobgames.com/pathfinding/a-star/implementation.html#python

        """
        # First check that the arguments were valid.
        self._check_pos_exist([initial, target])

        # Initialize the dicts that help us keep track
        came_from = {}
        cost_so_far = {}
        came_from[initial] = None
        cost_so_far[initial] = 0

        # Since it’s A* we use a heap queue to ensure that we always get the next node
        # with to lowest *guesstimated* distance to the current node.
        to_visit = []
        heapq.heappush(to_visit, (0, initial))

        while to_visit:
            old_prio, current = heapq.heappop(to_visit)

            if current == target:
                break

            for next in self[current]:
                new_cost = cost_so_far[current] + 1 # 1 is the cost to the neighbor
                if next not in cost_so_far or new_cost < cost_so_far[next]:  # only choose unvisited and ‘worthy’ nodes
                    cost_so_far[next] = new_cost
                    came_from[next] = current

                    # Add the node with an estimated distance to the heap
                    priority = new_cost + manhattan_dist(target, next)
                    heapq.heappush(to_visit, (priority, next))
        else:
            # no target found
            raise NoPathException("a_star: No path from %r to %r." % (initial, target))

        # Now back-track using seen to determine how we got here.
        # Initialise the path with current node, i.e. position of food.
        current = target
        path = [current]
        while current != initial:
            current = came_from[current]
            path.append(current)
        # The last element is the current position, we don’t need that in our
        # path, so don’t include it.
        return path[:-1]

