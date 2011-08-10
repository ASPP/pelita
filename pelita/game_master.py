# -*- coding: utf-8 -*-

""" The controller """

import copy
import random
import heapq
from pelita.containers import TypeAwareList
from pelita import datamodel
from pelita.player import AbstractPlayer
from pelita.viewer import AbstractViewer

__docformat__ = "restructuredtext"

class PlayerTimeout(Exception):
    pass

class PlayerDisconnected(Exception):
    pass

class GameMaster(object):
    """ Controller of player moves and universe updates.

    This object coordinates the moves of the player implementations with the
    updating of the universe.

    Parameters
    ----------
    universe : Universe
        the game state
    game_time : int
        the total permitted number of rounds
    number_bots : int
        the total number of bots
    player_teams : the participating player teams
    player_teams_bots : stores for each player_team index which bots it has
    viewers : list of subclasses of AbstractViewer
        the viewers that are observing this game

    """
    def __init__(self, layout, number_bots, game_time):
        self.universe = datamodel.create_CTFUniverse(layout, number_bots)
        self.game_time = game_time
        self.number_bots = number_bots
        self.player_teams = []
        self.viewers = []

    def register_team(self, team, team_name=""):
        """ Register a client TeamPlayer class.

        Parameters
        ----------
        team : class which calculates a new move for
            each Bot of the team.
        """
        self.player_teams.append(team)

        # map a player_team to a universe.team 1:1
        team_idx = len(self.player_teams) - 1

        # set the name in the universe
        if team_name:
            self.universe.teams[team_idx].name = team_name

    def register_viewer(self, viewer):
        """ Register a viewer to display the game state as it progresses.

        Parameters
        ----------
        viewer : subclass of AbstractViewer

        """
        if (viewer.__class__.observe.__func__ ==
                AbstractViewer.observe.__func__):
            raise TypeError("Viewer %s does not override 'observe()'."
                    % viewer.__class__)
        viewer.set_initial(self.universe.copy())
        self.viewers.append(viewer)

    def set_initial(self):
        """ This method needs to be called before a game is started.
        It notifies the PlayerTeams of the initial universes and their
        respective bot_ids.
        """
        for team_idx, team in enumerate(self.player_teams):
            # the respective bot ids in the universe
            team._set_bot_ids(self.universe.teams[team_idx].bots)
            team._set_initial(self.universe.copy())

    # TODO the game winning detection should be refactored

    def play(self):
        """ Play a whole game. """
        # notify all PlayerTeams
        self.set_initial()

        if len(self.player_teams) != len(self.universe.teams):
            raise IndexError(
                "Universe uses %i teams, but only %i are registered."
                % (len(self.player_teams), len(self.universe.teams)))
        for gt in range(self.game_time):
            if not self.play_round(gt):
                return

    def play_round(self, current_game_time):
        """ Play only a single round.

        A single round is defined as all bots moving once.

        Parameters
        ----------
        current_game_time : int
            the number of this round

        """
        for i, bot in enumerate(self.universe.bots):
            player_team = self.player_teams[bot.team_index]
            try:
                move = player_team._get_move(bot.index, self.universe.copy())
                events = self.universe.move_bot(i, move)
            except (datamodel.IllegalMoveException, PlayerTimeout):
                moves = self.universe.get_legal_moves(bot.current_pos).keys()
                moves.remove(datamodel.stop)
                if not moves:
                    moves = [datamodel.stop]

                move = random.choice(moves)
                events = self.universe.move_bot(i, move)
                events.append(datamodel.TimeoutEvent(bot.team_index))
            except PlayerDisconnected:
                other_team_idx = not bot.team_index

                events = TypeAwareList(base_class=datamodel.UniverseEvent)
                events.append(datamodel.TeamWins(other_team_idx))

            for timeout_event in events.filter_type(datamodel.TimeoutEvent):
                team = self.universe.teams[timeout_event.team_index]
                # team.score -= 1

            for v in self.viewers:
                v.observe(current_game_time, i, self.universe.copy(), copy.deepcopy(events))
            if datamodel.TeamWins in events:
                return False
        return True

class UniverseNoiser(object):
    """ Class to make bot positions noisy.

    Supports uniform noise in maze space. Can be extended to support other types
    of noise. Noise will only be applied if the enemy bot is with a certain
    threshold (`sight_distance`).

    Parameters
    ----------
    universe : CTFUniverse
        the universe which will later be used
    noise_radius : int, optional, default: 5
        the radius for the uniform noise
    sight_distance : int, optional, default: 5
        the distance at which noise is no longer applied.

    """

    def __init__(self, universe, noise_radius=5, sight_distance=5):
        self.adjacency = dict((pos, universe.get_legal_moves(pos).values())
                for pos in universe.maze.pos_of(datamodel.Free))
        self.noise_radius = noise_radius
        self.sight_distance = sight_distance

    def pos_within(self, position):
        """ Position within a certain distance. """
        if position not in self.adjacency.keys():
            raise TypeError("%s is not a free space in this maze" % repr(position))
        positions = set()
        to_visit = [position]
        for i in range(self.noise_radius):
            local_to_visit = []
            for pos in to_visit:
                if pos not in positions:
                    positions.add(pos)
                local_to_visit.extend(self.adjacency[pos])
            to_visit = local_to_visit
        return positions

    def a_star(self, initial, target):
        """ A* search. """
        to_visit = []
        # seen needs to be list since we use it for backtracking
        # a set would make the lookup faster, but not enable backtracking
        seen = []
        # since its A* we use a heap que
        # this ensures we always get the next node with to lowest manhatten
        # distance to the current node
        heapq.heappush(to_visit, (0, (initial)))
        while to_visit:
            man_dist, current = heapq.heappop(to_visit)
            if current in seen:
                continue
            elif current == target:
                break
            else:
                seen.append(current)
                for pos in self.adjacency[current]:
                    heapq.heappush(to_visit, (datamodel.manhattan_dist(target, pos), (pos)))

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

    def uniform_noise(self, universe, bot_index):
        """ Apply uniform noise to the enemies of a Bot.

        Given a `bot_index` the method looks up the enemies of this bot. It then
        adds uniform noise in maze space to the enemy positions. If a position
        is noisy or not is indicated by the `noisy` attribute in the Bot class.

        The method will modify the reference, therefore it is important to use a
        copy of the universe as an argument.

        Parameters
        ----------
        universe : CTFUniverse
            the universe to add noise to
        bot_index : int
            the bot whose enemies should be noisy

        Returns
        -------
        noisy_universe : CTFUniverse
            universe with noisy enemy positions

        """
        bot = universe.bots[bot_index]
        bots_to_noise = universe.enemy_bots(bot.team_index)
        for b in bots_to_noise:
            if len(self.a_star(bot.current_pos, b.current_pos)) > self.sight_distance:
                possible_positions = list(self.pos_within(b.current_pos))
                b.current_pos = random.choice(possible_positions)
                b.noisy = True
        return universe

