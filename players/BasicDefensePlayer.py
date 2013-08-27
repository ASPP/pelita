# -*- coding: utf-8 -*-

from pelita import datamodel
from pelita.player import AbstractPlayer, SimpleTeam
from pelita.graph import AdjacencyList, NoPathException, diff_pos

class BasicDefensePlayer(AbstractPlayer):
    """ A crude defensive player.

    Will move towards the border, and as soon as it notices enemies in its
    territory, it will start to track them. When it kills the enemy it returns
    to the border and waits there for more. Like the BFSPlayer this player
    stores the maze as an adjacency list [1] but uses the breadth first search [2] to
    find the closest position on the border.  However it additionally uses the
    A* (A Star) search [3] to find the shortest path to its target.

    The adjacency lits representation (AdjacencyList) and A* search
    (AdjacencyList.a_star) are imported from pelita.graph.

    * [1] http://en.wikipedia.org/wiki/Adjacency_list
    * [2] http://en.wikipedia.org/wiki/Breadth-first_search
    * [3] http://en.wikipedia.org/wiki/A*_search_algorithm

    """
    def set_initial(self):
        self.adjacency = AdjacencyList(self.current_uni.reachable([self.initial_pos]))
        self.path = self.path_to_border
        self.tracking_idx = None

    @property
    def path_to_border(self):
        """ Path to the closest border position. """
        try:
            return self.adjacency.bfs(self.current_pos, self.team_border)
        except NoPathException:
            return None

    @property
    def path_to_target(self):
        """ Path to the target we are currently tracking. """
        try:
            return self.adjacency.a_star(self.current_pos,
                    self.tracking_target.current_pos)
        except NoPathException:
            return None

    @property
    def tracking_target(self):
        """ Bot object we are currently tracking. """
        return self.current_uni.bots[self.tracking_idx]

    def get_move(self):
        # if we were killed, for whatever reason, reset the path
        if self.current_pos == self.initial_pos or self.path is None:
            self.path = self.path_to_border

        # First we need to check, if our tracked enemy is still
        # in our zone
        if self.tracking_idx is not None:
            # if the enemy is no longer in our zone
            if not self.team.in_zone(self.tracking_target.current_pos):
                self.tracking_idx = None
                self.path = self.path_to_border
            # otherwise update the path to the target
            else:
                self.path = self.path_to_target

        # if we are not currently tracking anything
        # (need to check explicity for None, because using 'if 
        # self.tracking_idx' would evaluate to True also when we are tracking
        # the bot with index == 0)
        if self.tracking_idx is None:
            # check the enemy positions
            possible_targets = [enemy for enemy in self.enemy_bots
                    if self.team.in_zone(enemy.current_pos)]
            if possible_targets:
                # get the path to the closest one
                try:
                    possible_paths = [(enemy, self.adjacency.a_star(self.current_pos, enemy.current_pos))
                                      for enemy in possible_targets]
                except NoPathException:
                    possible_paths = []
            else:
                possible_paths = []

            if possible_paths:
                closest_enemy, path = min(possible_paths,
                                          key=lambda enemy_path: len(enemy_path[1]))

                # track that bot by using its index
                self.tracking_idx = closest_enemy.index
                self.path = path
            else:
                # otherwise keep going if we aren't already underway
                if not self.path:
                    self.path = self.path_to_border

        # if something above went wrong, just stand still
        if not self.path:
            return datamodel.stop
        else:
            return diff_pos(self.current_pos, self.path.pop())

def factory():
    return SimpleTeam("The BasicDefensePlayers", BasicDefensePlayer(), BasicDefensePlayer())

