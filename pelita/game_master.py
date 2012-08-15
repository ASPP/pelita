# -*- coding: utf-8 -*-

""" The controller """

import random
import sys
import time
from . import datamodel
from .graph import NoPathException
from .datamodel import CTFUniverse, Bot, Free, manhattan_dist
from .graph import AdjacencyList

__docformat__ = "restructuredtext"

class GameFinished(Exception):
    pass

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
    seed : int, optional
        seed which initialises the internal random number generator

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
    def __init__(self, layout, number_bots, game_time, noise=True, noiser=None,
                 initial_delay=0.0, max_timeouts=5, timeout_length=3, layout_name=None,
                 seed=None):
        self.universe = datamodel.create_CTFUniverse(layout, number_bots)
        self.number_bots = number_bots
        if noiser is None:
            noiser = ManhattanNoiser
        self.noiser = noiser(self.universe, seed=seed) if noise else None
        self.player_teams = []
        self.player_teams_timeouts = []
        self.viewers = []
        self.initial_delay = initial_delay

        # We seed the internal random number generator.
        # This instance should be used for all important random decisions
        # in GameMaster which influence the game itself.
        # E.g. for forced random moves and most importantly for calculating
        # the seed which is passed to the clients with set_initial.
        # Currently, the noiser does not use this rng but has its own.
        self.rnd = random.Random(seed)

        #: The pointer to the current iteration.
        self._step_iter = None

        self.game_state = {
            "bot_moved": [],
            "food_eaten": [],
            "bot_destroyed": [],
            "timeout_teams": [0] * len(self.universe.teams),
            "bot_id": None,
            "round_index": None,
            "running_time": 0,
            "finished": False,
            "team_time": [0] * len(self.universe.teams),
            "times_killed": [0] * len(self.universe.teams),
            "team_wins": None,
            "game_draw": None,
            "game_time": game_time,
            "food_count": [0] * len(self.universe.teams),
            "food_to_eat": [len(self.universe.enemy_food(team.index)) for team in self.universe.teams],
            "timeout_length": timeout_length,
            "max_timeouts": max_timeouts,
            "bot_talk": [""] * self.number_bots,
            "layout_name": layout_name,
            "noise_radius": self.noiser and self.noiser.noise_radius,
            "noise_sight_distance": self.noiser and self.noiser.sight_distance
        }

    @property
    def game_time(self):
        return self.game_state["game_time"]

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
        self.viewers.append(viewer)

    def update_viewers(self):
        """ Call the 'observe' method on all registered viewers.
        """
        for viewer in self.viewers:
            viewer.observe(self.universe,
                           self.game_state)

    def set_initial(self):
        """ This method needs to be called before a game is started.
        It notifies the PlayerTeams and the Viewers of the initial
        universes and tells the PlayerTeams what team_id they have.
        """
        if len(self.player_teams) != len(self.universe.teams):
            raise IndexError(
                "Universe uses %i teams, but %i are registered."
                % (len(self.player_teams), len(self.universe.teams)))

        for team_id, team in enumerate(self.player_teams):
            # What follows is a small hack:
            # We only send the seed once with the game state
            # during set_initial. This ensures that no-one
            # is able to read or guess the seed of the other
            # party.

            team_seed = self.rnd.randint(0, sys.maxint)
            team_state = dict({"seed": team_seed}, **self.game_state)
            team.set_initial(team_id, self.universe, team_state)

        for viewer in self.viewers:
            viewer.set_initial(self.universe)

    # TODO the game winning detection should be refactored
    def play(self):
        """ Play game until finished. """
        # notify all PlayerTeams
        self.set_initial()

        time.sleep(self.initial_delay)

        while not self.game_state.get("finished"):
            self.play_round()

    def play_round(self):
        """ Finishes the current round.

        A round is defined as all bots moving once.
        """
        if self.game_state["finished"]:
            return

        if self._step_iter is None:
            self._step_iter = self._play_bot_iterator()
        try:
            while True:
                self._step_iter.next()
        except StopIteration:
            self._step_iter = None
            # at the end of iterations
        except GameFinished:
            return

    def play_step(self):
        """ Plays a single step of a bot.
        """
        if self.game_state["finished"]:
            return

        if self._step_iter is None:
            self._step_iter = self._play_bot_iterator()

        try:
            self._step_iter.next()
        except StopIteration:
            self._step_iter = None
            # we could not make a move:
            # just try another one
            self.play_step()
        except GameFinished:
            return

    def _play_bot_iterator(self):
        """ Returns an iterator which will query a bot at each step.
        """
        self.prepare_next_round()

        if not self.game_state.get("finished"):
            self.check_finished()
            self.check_winner()

            self.print_possible_winner()

        if self.game_state.get("finished"):
            self.update_viewers()
            raise GameFinished()

        for bot in self.universe.bots:
            start_time = time.time()

            self._play_bot(bot)

            end_time = time.time()
            self.game_state["running_time"] += (end_time - start_time)

            self.update_viewers()

            # give control to caller
            yield

        self.check_finished()
        self.check_winner()

        self.print_possible_winner()

        if self.game_state.get("finished"):
            self.update_viewers()

    def _play_bot(self, bot):
        self.game_state["bot_id"] = bot.index
        self.game_state["bot_moved"] = []
        self.game_state["food_eaten"] = []
        self.game_state["bot_destroyed"] = []

        player_team = self.player_teams[bot.team_index]
        try:
            if self.noiser:
                universe = self.noiser.uniform_noise(self.universe, bot.index)
            else:
                universe = self.universe

            team_time_begin = time.time()

            player_state = player_team.get_move(bot.index, universe, self.game_state)
            try:
                # player_state may be None, if RemoteTeamPlayer could not
                # properly convert it
                move = player_state.get("move")
                bot_talk = player_state.get("say")
            except AttributeError:
                raise datamodel.IllegalMoveException("Bad data returned by Player.")

            self.game_state["bot_talk"][bot.index] = bot_talk

            team_time_needed = time.time() - team_time_begin
            self.game_state["team_time"][bot.team_index] += team_time_needed

            move_state = self.universe.move_bot(bot.index, move)
            for k, v in move_state.iteritems():
                self.game_state[k] += v

        except (datamodel.IllegalMoveException, PlayerTimeout):
            # after max_timeouts timeouts, you lose
            self.game_state["timeout_teams"][bot.team_index] += 1

            if self.game_state["timeout_teams"][bot.team_index] == self.game_state["max_timeouts"]:
                other_team = self.universe.enemy_team(bot.team_index)
                self.game_state["team_wins"] = other_team.index
                sys.stderr.write("Timeout #%r for team %r (bot index %r). Team disqualified.\n" % (
                                  self.game_state["timeout_teams"][bot.team_index],
                                  bot.team_index,
                                  bot.index))
            else:
                sys.stderr.write("Timeout #%r for team %r (bot index %r).\n" % (
                                  self.game_state["timeout_teams"][bot.team_index],
                                  bot.team_index,
                                  bot.index))

            moves = self.universe.get_legal_moves_or_stop(bot.current_pos).keys()

            move = self.rnd.choice(moves)
            move_state = self.universe.move_bot(bot.index, move)
            for k,v in move_state.iteritems():
                self.game_state[k] += v

        except PlayerDisconnected:
            other_team = self.universe.enemy_team(bot.team_index)
            self.game_state["team_wins"] = other_team.index

            sys.stderr.write("Team %r (bot index %r) disconnected. Team disqualified.\n" % (
                              bot.team_index,
                              bot.index))

        for food_eaten in self.game_state["food_eaten"]:
            team_id = self.universe.bots[food_eaten["bot_id"]].team_index
            self.game_state["food_count"][team_id] += 1

        for destroyed in self.game_state["bot_destroyed"]:
            self.game_state["times_killed"][self.universe.bots[destroyed["bot_id"]].team_index] += 1


    def prepare_next_round(self):
        """ Increases `game_state["round_index"]`, if possible
        and resets `game_state["bot_id"]`.
        """
        if self.game_state.get("finished"):
            return

        self.game_state["bot_id"] = None

        if self.game_state["round_index"] is None:
            self.game_state["round_index"] = 0
        elif self.game_state["round_index"] < self.game_time:
            self.game_state["round_index"] += 1
        else:
            self.game_state["finished"] = True

    def check_finished(self):
        self.game_state["finished"] = False

        if (self.game_state["team_wins"] is not None or
            self.game_state["game_draw"] is not None):
            self.game_state["finished"] = True

        if self.game_state["round_index"] >= self.game_time:
            self.game_state["finished"] = True
            # clear the bot_id of the current bot
            self.game_state["bot_id"] = None
        else:
            for to_eat, eaten in zip(self.game_state["food_to_eat"], self.game_state["food_count"]):
                if to_eat == eaten:
                    self.game_state["finished"] = True


    def check_winner(self):
        if not self.game_state["finished"]:
            return

        if (self.game_state["team_wins"] is not None or
            self.game_state["game_draw"] is not None):
            # we found out already
            return

        if self.universe.teams[0].score > self.universe.teams[1].score:
            self.game_state["team_wins"] = 0
        elif self.universe.teams[0].score < self.universe.teams[1].score:
            self.game_state["team_wins"] = 1
        else:
            self.game_state["game_draw"] = True

    def print_possible_winner(self):
        """ Checks the event list for a potential winner and prints this information.

        This is needed for scripts parsing the output.
        """
        winning_team = self.game_state.get("team_wins")
        if winning_team is not None:
            winner = self.universe.teams[winning_team]
            loser = self.universe.enemy_team(winning_team)
            msg = "Finished. %r won over %r. (%r:%r)" % (
                    winner.name, loser.name,
                    winner.score, loser.score
                )

            sys.stdout.flush()
        elif self.game_state.get("game_draw") is not None:
            t0 = self.universe.teams[0]
            t1 = self.universe.teams[1]
            msg = "Finished. %r and %r had a draw. (%r:%r)" % (
                    t0.name, t1.name,
                    t0.score, t1.score
                )
        else:
            return

        print msg
        # We must manually flush, else our forceful stopping of Tk
        # won't let us pipe it.
        sys.stdout.flush()


class UniverseNoiser(object):
    """Abstract BaseClass to make bot positions noisy.

    Supports uniform noise in maze space. Can be extended to support other types
    of noise. Noise will only be applied if the enemy bot is with a certain
    threshold (`sight_distance`).

    Derived classes will need to implement distance and the alter_pos methods

    Methods
    -------

    distance(bot, other_bot):
        return distance between current bot and bot to be noised. Distance
        is measured in the space relevant to the particular algorithm implemented
        in the subclass, e.g. maze distance, manhattan distance, euclidean distance...

    alter_pos(bot_pos):
        return the noised new position of an enemy bot.

    Parameters
    ----------
    universe : CTFUniverse
        the universe which will later be used
    noise_radius : int, optional, default: 5
        the radius for the uniform noise
    sight_distance : int, optional, default: 5
        the distance at which noise is no longer applied.
    seed : int, optional
        seed which initialises the internal random number generator

    """

    def __init__(self, universe, noise_radius=5, sight_distance=5, seed=None):
        self.adjacency = AdjacencyList(universe)
        self.noise_radius = noise_radius
        self.sight_distance = sight_distance
        self.rnd = random.Random(seed)

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
        universe_copy = CTFUniverse(maze=universe.maze, teams=universe.teams, bots=[Bot._from_json_dict(bot._to_json_dict()) for bot in universe.bots])
        self.universe = universe_copy
        bot = universe_copy.bots[bot_index]
        bots_to_noise = universe_copy.enemy_bots(bot.team_index)
        for b in bots_to_noise:
            # Check that the distance between this bot and the enemy is larger
            # than `sight_distance`.
            distance = self.distance(bot, b)

            if distance is None or distance > self.sight_distance:
                # If so then alter the position of the enemy
                b.current_pos = self.alter_pos(b.current_pos)
                b.noisy = True

        return universe_copy

    def distance(self, bot, other_bot):
        return NotImplementedError

    def alter_pos(self, bot_pos):
        return NotImplementedError


class AStarNoiser(UniverseNoiser):
    """Noiser in maze space.

    It uses A* and adjacency maps to measure distances in maze space."""
    def __init__(self, universe, noise_radius=5, sight_distance=5):
        super(AStarNoiser, self).__init__(universe, noise_radius, sight_distance)
        self.adjacency = AdjacencyList(universe)

    def distance(self, bot, other_bot):
        try:
            return len(self.adjacency.a_star(bot.current_pos, other_bot.current_pos))
        except NoPathException:
            # We cannot see it: Apply the noise anyway
            return None

    def alter_pos(self, bot_pos):
        possible_positions = list(self.adjacency.pos_within(bot_pos,
                                                            self.noise_radius))
        if len(possible_positions) > 0:
            return self.rnd.choice(possible_positions)
        else:
            return bot_pos

class ManhattanNoiser(UniverseNoiser):
    """Noiser in Manhattan space.

    It uses Manhattan distance. This noiser is much faster than AStarNoiser,
    but Manhattan distance is less relevant to the game. For example, a bot
    distant 1 in Manhattan space could still be much further in maze distance."""

    def distance(self, bot, other_bot):
        return manhattan_dist(bot.current_pos, other_bot.current_pos)

    def alter_pos(self, bot_pos):
        # get a list of possible positions
        noise_radius = self.noise_radius
        x_min, x_max = bot_pos[0] - noise_radius, bot_pos[0] + noise_radius
        y_min, y_max = bot_pos[1] - noise_radius, bot_pos[1] + noise_radius
        possible_positions = [(i,j) for i in range(x_min, x_max)
                                    for j in range(y_min, y_max)
                              if manhattan_dist((i,j), bot_pos) <= noise_radius]

        # shuffle the list of positions
        self.rnd.shuffle(possible_positions)
        for pos in possible_positions:
            try:
                # check that the bot can really fit in here
                if Free in self.universe.maze[pos]:
                    return pos
            except IndexError:
                pass
        # if we land here, no valid position has been found
        return bot_pos
