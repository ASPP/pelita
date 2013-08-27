# -*- coding: utf-8 -*-

from pelita import datamodel
from pelita.player import AbstractPlayer, SimpleTeam
from pelita.graph import AdjacencyList, NoPathException, diff_pos

class BFSPlayer(AbstractPlayer):
    """ This player uses breadth first search to always go to the closest food.

    This player uses an adjacency list [1] to store the topology of the
    maze. It will then do a breadth first search [2] to search for the
    closest food. When found, it will follow the determined path until it
    reaches the food. This continues until all food has been eaten or the
    enemy wins.

    The adjacency lits representation (AdjacencyList) and breadth first search
    (AdjacencyList.bfs) are imported from pelita.graph.

    * [1] http://en.wikipedia.org/wiki/Adjacency_list
    * [2] http://en.wikipedia.org/wiki/Breadth-first_search

    """
    def set_initial(self):
        # Before the game starts we initialise our adjacency list.
        self.adjacency = AdjacencyList(self.current_uni.reachable([self.initial_pos]))
        self.current_path = self.bfs_food()

    def bfs_food(self):
        """ Breadth first search for food.

        Returns
        -------
        path : a list of tuples (int, int)
            The positions (x, y) in the path from the current position to the
            closest food. The first element is the final destination.

        """
        try:
            return self.adjacency.bfs(self.current_pos, self.enemy_food)
        except NoPathException:
            return [self.current_pos]

    def get_move(self):
        if self.current_pos == self.initial_pos:
            # we have probably been killed
            # reset the path
            self.current_path = None
        if not self.current_path:
            self.current_path = self.bfs_food()
        new_pos = self.current_path.pop()
        move = diff_pos(self.current_pos, new_pos)

        if move in self.legal_moves:
            return move
        else:
            # Whoops. We’re lost.
            # If there was a timeout, and we are no longer where we think we
            # were, calculate a new path.
            self.current_path = None
            return self.get_move()

def factory():
    return SimpleTeam("The BFSPlayers", BFSPlayer(), BFSPlayer())
