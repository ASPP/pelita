# -*- coding: utf-8 -*-

""" Basic graph module """

from collections import deque
from pelita.datamodel import Maze, Free

__docformat__ = "restructuredtext"

class NoPathException(Exception):
    pass

class AdjacencyList(dict):

    def __init__(self, universe):
        # Get the list of all free positions.
        free_pos = universe.maze.pos_of(Free)
        # Here we use a generator on a dictionary to create the adjacency list.
        self.adjacency = dict((pos, universe.get_legal_moves(pos).values())
                for pos in free_pos)

    def bfs(self, initial, targets):
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
                to_visit.extend(self.adjacency[current])
        # if we did not find any food, we simply return a path with only the
        # current position
        if not found:
            return [initial]
        # Now back-track using seen to determine how we got here.
        # Initialise the path with current node, i.e. position of food.
        path = [current]
        while seen:
            # Pop the latest node in seen
            next_ = seen.pop()
            # If that's adjacent to the current node
            # it's in the path
            if next_ in self.adjacency[current]:
                # So add it to the path
                path.append(next_)
                # And continue back-tracking from there
                current = next_
        # The last element is the current position, we don't need that in our
        # path, so don't include it.
        return path[:-1]
