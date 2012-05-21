# -*- coding: utf-8 -*-

""" The controller """

import copy
import random
import sys
import time
from .containers import TypeAwareList
from . import datamodel
from .graph import NoPathException
from .viewer import AbstractViewer
from .graph import AdjacencyList

__docformat__ = "restructuredtext"

MAX_TIMEOUTS = 5

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
    layout : string
        initial layout as string
    number_bots : int
        the total number of bots
    game_time : int
        the total permitted number of rounds
    noise : boolean
        should enemy positions be noisy

    Attributes
    ----------
    universe : CTFUniverse
        the game state
    noiser : UniverseNoiser or None
        object to add noise to enemy positions
    player_teams : list
        the participating player teams
    viewers : list of subclasses of AbstractViewer
        the viewers that are observing this game

    """
    def __init__(self, layout, number_bots, game_time, noise=True,
                 initial_delay=0.0):
        self.universe = datamodel.create_CTFUniverse(layout, number_bots)
        self.number_bots = number_bots
        self.game_time = game_time
        self.noiser = UniverseNoiser(self.universe) if noise else None
        self.player_teams = []
        self.player_teams_timeouts = []
        self.viewers = []
        self.initial_delay = initial_delay
        self.events = {
            "bot_moved": [],
            "food_eaten": [],
            "bot_destroyed": [],
            "timeout_teams": [0, 0],
            "score": [0, 0],
            "bot_id": None,
            "round_index": None,
            "running_time": 0,
            "team_wins": None,
            "game_draw": None
        }

    def register_team(self, team, team_name=""):
        """ Register a client TeamPlayer class.

        Parameters
        ----------
        team : class which calculates a new move for
            each Bot of the team.
        """
        self.player_teams.append(team)
        self.player_teams_timeouts.append(0)

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
        self.viewers.append(viewer)

    def send_to_viewers(self, round_index, turn, events):
        """ Call the 'observe' method on all registered viewers.

        Parameters
        ----------
        round_index : int
            the current round
        turn : int
            the current turn
        events : TypeAwareList of UniverseEvent
            the events for this turn
        """
        for viewer in self.viewers:
            viewer.observe(round_index,
                    turn,
                    self.universe.copy(),
                    copy.deepcopy(events))

    def set_initial(self):
        """ This method needs to be called before a game is started.
        It notifies the PlayerTeams and the Viewers of the initial
        universes and tells the PlayerTeams what their respective
        bot_ids are.
        """
        for team_idx, team in enumerate(self.player_teams):
            # the respective bot ids in the universe
            team._set_bot_ids(self.universe.teams[team_idx].bots)
            team._set_initial(self.universe.copy())

        for viewer in self.viewers:
            viewer.set_initial(self.universe.copy())

    # TODO the game winning detection should be refactored

    def play(self):
        """ Play a whole game. """
        # notify all PlayerTeams
        self.set_initial()
        
        time.sleep(self.initial_delay)

        if len(self.player_teams) != len(self.universe.teams):
            raise IndexError(
                "Universe uses %i teams, but only %i are registered."
                % (len(self.player_teams), len(self.universe.teams)))

        start_time = time.time()

        while True:
            running = self.play_round()
            if not running:
                break

        end_time = time.time()
        self.events["running_time"] = end_time - start_time

        if self.events["score"][0] > self.events["score"][1]:
            self.events["team_wins"] = 0
        elif self.events["score"][0] < self.events["score"][1]:
            self.events["team_wins"] = 1
        else:
            self.events["game_draw"] = True

        self.print_possible_winner()

        self.send_to_viewers(self.events["round_index"], None, self.events)

    def play_round(self):
        """ Play only a single round.

        A single round is defined as all bots moving once.

        Returns
        -------
        game_running : boolean
            True, if game is still running, False otherwise.
        """
        if self.events["round_index"] is None:
            self.events["round_index"] = 0
        elif self.events["round_index"] >= self.game_time:
            # This could raise an exception.
            return False

        for i, bot in enumerate(self.universe.bots):
            self.events["bot_id"] = i
            self.events["bot_moved"] = []
            self.events["food_eaten"] = []
            self.events["bot_destroyed"] = []

            player_team = self.player_teams[bot.team_index]
            try:
                universe_copy = self.universe.copy()
                if self.noiser:
                    universe_copy = self.noiser.uniform_noise(universe_copy, bot.index)
                move = player_team._get_move(bot.index, universe_copy)
                self.events = self.universe.move_bot(self.events, move)

            except (datamodel.IllegalMoveException, PlayerTimeout) as e:
                # after MAX_TIMEOUTS timeouts, you lose
                self.events["timeout_teams"][bot.team_index] += 1

                if self.events["timeout_teams"][bot.team_index] == MAX_TIMEOUTS:
                    other_team_idx = not bot.team_index
                    self.events["team_wins"] = other_team_idx
                    sys.stderr.write("Timeout #%r for team %r (bot index %r). Team disqualified.\n" % (
                                      self.events["timeout_teams"][bot.team_index],
                                      bot.team_index,
                                      bot.index))
                else:
                    sys.stderr.write("Timeout #%r for team %r (bot index %r).\n" % (
                                      self.events["timeout_teams"][bot.team_index],
                                      bot.team_index,
                                      bot.index))

                moves = self.universe.get_legal_moves(bot.current_pos).keys()
                moves.remove(datamodel.stop)
                if not moves:
                    moves = [datamodel.stop]

                move = random.choice(moves)
                self.events = self.universe.move_bot(self.events, move)

            except PlayerDisconnected:
                other_team_idx = not bot.team_index
                self.events["team_wins"] = other_team_idx

                sys.stderr.write("Team %r (bot index %r) disconnected. Team disqualified.\n" % (
                                  bot.team_index,
                                  bot.index))

            self.print_possible_winner()

            self.send_to_viewers(self.events["round_index"], bot.index, self.events)

            if self.events.get("team_wins") is not None or self.events.get("game_draw") is not None:
                return False

        self.events["round_index"] += 1
        return True

    def print_possible_winner(self):
        """ Checks the event list for a potential winner and prints this information.

        This is needed for scripts parsing the output.
        """
        winning_team = self.events.get("team_wins")
        if winning_team is not None:
            winner = self.universe.teams[winning_team]
            loser = self.universe.teams[1 - winning_team]
            print "Finished. %r won over %r. (%r:%r)" % (
                    winner.name, loser.name,
                    winner.score, loser.score
                )
            # We must manually flush, else our forceful stopping of Tk
            # won't let us pipe it.
            sys.stdout.flush()

        if self.events.get("game_draw") is not None:
            t0 = self.universe.teams[0]
            t1 = self.universe.teams[1]
            print "Finished. %r and %r had a draw. (%r:%r)" % (
                    t0.name, t1.name,
                    t0.score, t1.score
                )
            sys.stdout.flush()



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

    Attributes
    ----------
    adjacency : AdjacencyList
        adjacency list representation of the Maze

    """

    def __init__(self, universe, noise_radius=5, sight_distance=5):
        self.adjacency = AdjacencyList(universe)
        self.noise_radius = noise_radius
        self.sight_distance = sight_distance

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
            # Check that the distance between this bot and the enemy is larger
            # than `sight_distance`.
            try:
                distance = len(self.adjacency.a_star(bot.current_pos, b.current_pos))
            except NoPathException:
                # We cannot see it: Apply the noise anyway
                distance = None

            if distance is None or distance > self.sight_distance:
                # If so then alter the position of the enemy
                possible_positions = list(self.adjacency.pos_within(b.current_pos,
                    self.noise_radius))
                b.current_pos = random.choice(possible_positions)
                b.noisy = True
        return universe

