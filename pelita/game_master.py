""" The controller """

import abc
import random
import sys
import time

from . import datamodel
from .datamodel import Bot, CTFUniverse
from .graph import AdjacencyList, NoPathException, manhattan_dist


class GameFinished(Exception):
    pass

class PlayerTimeout(Exception):
    pass

class PlayerDisconnected(Exception):
    pass

class GameMaster:
    """ Controller of player moves and universe updates.

    This object coordinates the moves of the player implementations with the
    updating of the universe.


    Parameters
    ----------
    layout : string
        initial layout as string
    teams : list of teams
        the teams to play the game
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
    def __init__(self, layout, teams, number_bots, game_time, noise=True, noiser=None,
                 initial_delay=0.0, max_timeouts=5, timeout_length=3, layout_name=None,
                 seed=None):
        self.universe = datamodel.CTFUniverse.create(layout, number_bots)
        self.number_bots = number_bots

        if not len(teams) == len(self.universe.teams):
            raise ValueError("Number of registered teams does not match the universe.")
        self.player_teams = teams

        if noiser is None:
            noiser = ManhattanNoiser
        self.noiser = noiser(self.universe, seed=seed) if noise else None

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
            #: holds a list of bot movements for this step
            #: [{"bot_id": bot_id, "old_pos": old_pos, "new_pos": new_pos}]
            "bot_moved": [],

            #: holds a list of eaten food items for this step
            #: [{"bot_id": bot_id, "food_pos": bot.current_pos}]
            "food_eaten": [],

            #: holds a list of destroyed bots for this step
            #: [{'bot_id': bot.index, 'destroyed_by': enemy.index}]
            "bot_destroyed": [],

            #: [timeouts_team_0, timeouts_team_1]
            "timeout_teams": [0] * len(self.universe.teams),

            #: bot.index of the bot which is about to move or None
            "bot_id": None,

            #: round_index or None,
            "round_index": None,

            #: time for all teams together
            "running_time": 0,

            #: true if finished
            "finished": False,

            #: [team_name_0, team_name_1]
            "team_name": [""] * len(self.universe.teams),

            #: [running_time_team_0, running_time_team_1]
            "team_time": [0] * len(self.universe.teams),

            #: [times_killed_team_0, times_killed_team_1]
            "times_killed": [0] * len(self.universe.teams),

            #: team.index of the team winning or None
            "team_wins": None,

            #: true if game is a draw
            "game_draw": None,

            #: {bot.index: reason} for a misbehaving bot
            "bot_error": {},

            #: [reason_team_0, reason_team_1] for a team which was disqualified
            "teams_disqualified": [None] * len(self.universe.teams),

            #: maximum number of rounds
            "game_time": game_time,

            #: [food_eaten_team_0, food_eaten_team_1]
            "food_count": [0] * len(self.universe.teams),

            #: [food_to_eat_team_0, food_to_eat_team_1]
            "food_to_eat": [len(self.universe.enemy_food(team.index)) for team in self.universe.teams],

            #: time until timeout
            "timeout_length": timeout_length,

            #: number of timeouts before game is lost
            "max_timeouts": max_timeouts,

            #: [talk_bot_0, talk_bot_1, ...]
            "bot_talk": [""] * self.number_bots,

            #: name of the layout
            "layout_name": layout_name,

            #: radius of the noise
            "noise_radius": self.noiser and self.noiser.noise_radius,

            #: sight distance of the noise
            "noise_sight_distance": self.noiser and self.noiser.sight_distance
        }

    @property
    def game_time(self):
        return self.game_state["game_time"]

    @property
    def finished(self):
        return self.game_state["finished"]

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

        for viewer in self.viewers:
            viewer.set_initial(self.universe)

        for team_id, team in enumerate(self.player_teams):
            # What follows is a small hack:
            # We only send the seed once with the game state
            # during set_initial. This ensures that no-one
            # is able to read or guess the seed of the other
            # party.

            team_seed = self.rnd.randint(0, sys.maxsize)
            team_state = dict({"seed": team_seed}, **self.game_state)
            try:
                team_name = team.set_initial(team_id, self.universe, team_state)
                self.game_state["team_name"][team_id] = team_name
            except PlayerTimeout:
                pass

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
                next(self._step_iter)
        except StopIteration:
            self._step_iter = None
            # at the end of iterations
        except GameFinished:
            self.update_viewers()

    def play_step(self):
        """ Plays a single step of a bot.
        """
        if self.game_state["finished"]:
            return

        if self._step_iter is None:
            self._step_iter = self._play_bot_iterator()

        try:
            next(self._step_iter)
        except StopIteration:
            self._step_iter = None
            # we could not make a move:
            # just try another one
            self.play_step()
        except GameFinished:
            self.update_viewers()

    def _play_bot_iterator(self):
        """ Returns an iterator which will query a bot at each step.
        """
        self.prepare_next_round()

        if self.check_finished():
            raise GameFinished()

        for bot in self.universe.bots:
            start_time = time.monotonic()

            self._play_bot(bot)

            end_time = time.monotonic()
            self.game_state["running_time"] += (end_time - start_time)

            if self.check_finished():
                raise GameFinished()

            self.update_viewers()

            # give control to caller
            yield

        self.game_state["bot_id"] = None

        if self.check_finished():
            raise GameFinished()

        if self.game_state.get("finished"):
            self.update_viewers()

    def _play_bot(self, bot):
        self.game_state["bot_id"] = bot.index
        self.game_state["bot_moved"] = []
        self.game_state["food_eaten"] = []
        self.game_state["bot_destroyed"] = []
        self.game_state["bot_timeout"] = None
        self.game_state["bot_error"] = {}

        player_team = self.player_teams[bot.team_index]
        try:
            if self.noiser:
                universe = self.noiser.uniform_noise(self.universe, bot.index)
            else:
                universe = self.universe

            team_time_begin = time.monotonic()

            player_state = player_team.get_move(bot.index, universe, self.game_state)
            try:
                # player_state may be None, if RemoteTeamPlayer could not
                # properly convert it
                move = player_state.get("move")
                bot_talk = player_state.get("say")
            except AttributeError:
                raise datamodel.IllegalMoveException("Bad data returned by Player.")

            self.game_state["bot_talk"][bot.index] = bot_talk

            team_time_end = time.monotonic()
            team_time_needed = team_time_end - team_time_begin
            self.game_state["team_time"][bot.team_index] += team_time_needed

            move_state = self.universe.move_bot(bot.index, move)
            for k, v in move_state.items():
                self.game_state[k] += v

        except (datamodel.IllegalMoveException, PlayerTimeout):
            # after max_timeouts timeouts, you lose
            self.game_state["timeout_teams"][bot.team_index] += 1
            self.game_state["bot_error"] = {bot.index: "timeout"}

            if self.game_state["timeout_teams"][bot.team_index] == self.game_state["max_timeouts"]:
                self.game_state["teams_disqualified"][bot.team_index] = "timeout"
            else:

                moves = list(self.universe.legal_moves_or_stop(bot.current_pos).keys())

                move = self.rnd.choice(moves)
                move_state = self.universe.move_bot(bot.index, move)
                for k, v in move_state.items():
                    self.game_state[k] += v

        except PlayerDisconnected:
            self.game_state["teams_disqualified"][bot.team_index] = "disconnected"

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
        if (self.game_state["team_wins"] is not None or
            self.game_state["game_draw"] is not None):
            self.game_state["finished"] = True
            return True

        teams_left = [team_id for team_id, reason in enumerate(self.game_state["teams_disqualified"]) if reason is None]
        if len(teams_left) == 1:
            # we have a survivor
            self.game_state["team_wins"] = teams_left[0]
            self.game_state["finished"] = True
            return True

        # If the round has finished, we may check, if we can end the game
        if self.game_state["bot_id"] is None:
            if self.game_state["round_index"] >= self.game_time:
                self.game_state["finished"] = True
            else:
                for to_eat, eaten in zip(self.game_state["food_to_eat"], self.game_state["food_count"]):
                    if to_eat == eaten:
                        self.game_state["finished"] = True

        if self.game_state["finished"]:
            if self.universe.teams[0].score > self.universe.teams[1].score:
                self.game_state["team_wins"] = 0
            elif self.universe.teams[0].score < self.universe.teams[1].score:
                self.game_state["team_wins"] = 1
            else:
                self.game_state["game_draw"] = True
            return True

        return self.game_state["finished"]

class UniverseNoiser(metaclass=abc.ABCMeta):
    """Abstract BaseClass to make bot positions noisy.

    Supports uniform noise in maze space. Can be extended to support other types
    of noise. Noise will only be applied if the enemy bot is with a certain
    threshold (`sight_distance`).

    Derived classes will need to implement distance and the altered_pos methods

    Methods
    -------

    distance(bot, other_bot):
        return distance between current bot and bot to be noised. Distance
        is measured in the space relevant to the particular algorithm implemented
        in the subclass, e.g. maze distance, manhattan distance, euclidean distance...

    altered_pos(bot_pos):
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
        self.adjacency = AdjacencyList(universe.free_positions())
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
        # Prepare a copy of the universe with all bots cloned so that their position
        # can be changed without altering the original universe.
        universe_copy = CTFUniverse(maze=universe.maze,
                                    food=universe.food,
                                    teams=universe.teams,
                                    bots=[Bot._from_json_dict(bot._to_json_dict()) for bot in universe.bots])
        self.universe = universe_copy
        current_bot = universe_copy.bots[bot_index]
        enemy_bots = universe_copy.enemy_bots(current_bot.team_index)
        for b in enemy_bots:
            # Check that the distance between this bot and the enemy is larger
            # than `sight_distance`.
            distance = self.distance(current_bot, b)

            if distance is None or distance > self.sight_distance:
                # If so then alter the position of the enemy
                b.current_pos = self.altered_pos(b.current_pos)
                b.noisy = True

        return universe_copy

    @abc.abstractmethod
    def distance(self, bot, other_bot):
        """ Method to return the noiser-relevant distance between two bots.
        """

    @abc.abstractmethod
    def altered_pos(self, bot_pos):
        """ Method to return a new position for a bot.
        """

class ManhattanNoiser(UniverseNoiser):
    """Noiser in Manhattan space.

    It uses Manhattan distance. A bot distance of 1 in Manhattan space
    could still be much further away in maze distance."""

    def distance(self, bot, other_bot):
        return manhattan_dist(bot.current_pos, other_bot.current_pos)

    def altered_pos(self, bot_pos):
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
                if not self.universe.maze[pos]:
                    return pos
            except KeyError:
                pass
        # if we land here, no valid position has been found
        return bot_pos
