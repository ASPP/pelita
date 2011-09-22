# -*- coding: utf-8 -*-

""" Basic graph module """

from collections import deque
import heapq
from .datamodel import Free, manhattan_dist

__docformat__ = "restructuredtext"

class NoPathException(Exception):
    pass

class NoPositionException(Exception):
    pass

class AdjacencyList(dict):
    """ Adjacency list [1] representation of a Maze.

    Implemented by inheriting from `dict`.

    [1] http://en.wikipedia.org/wiki/Adjacency_list

    """
    def __init__(self, universe):
        # Get the list of all free positions.
        free_pos = universe.maze.pos_of(Free)
        # Here we use a generator on a dictionary to create the adjacency list.
        self.update(dict((pos, universe.get_legal_moves(pos).values())
                for pos in free_pos))

    def pos_within(self, position, distance):
        """ Position within a certain distance.

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
        NoPositionException
            if either `initial` or `targets` does not exist

        """
        if position not in self.keys():
            raise NoPositionException("Position %s does not exist." %
                    repr(position))
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

    def bfs(self, initial, targets):
        """ Breadth first search (bfs).

        Breadth first search [1] from one position to multiple tragets. The
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
        for pos in [initial] + targets:
            if pos not in self.keys():
                raise NoPositionException("Position %s does not exist." %
                        repr(pos))
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
        # if we did not find any food, we simply return a path with only the
        # current position
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
        """ A* search. """
        to_visit = []
        # Seen needs to be list since we use it for backtracking.
        # A set would make the lookup faster, but backtracking impossible.
        seen = []
        # Since it's A* we use a heap queue to ensure that we always
        # get the next node with to lowest manhattan distance to the
        # current node.
        heapq.heappush(to_visit, (0, (initial)))
        while to_visit:
            man_dist, current = heapq.heappop(to_visit)
            if current in seen:
                continue
            elif current == target:
                break
            else:
                seen.append(current)
                for pos in self[current]:
                    heapq.heappush(to_visit, (manhattan_dist(target, pos), (pos)))

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
