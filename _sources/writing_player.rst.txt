.. _writing_a_player:

================
Writing a Player
================

This section explains how to write a player.

Introduction
============

To begin with, we must define a few classes and some terminology which will be
used throughout this documentation.


`pelita.datamodel.CTFUniverse`:
    The game’s universe. Holds a list of ``Bot`` instances, a list of ``Team``
    instances, a single ``Maze`` object and a list with the positions of food.
    Can be queried to obtain information about the game.

`pelita.datamodel.Bot`:
    The data structure used to store the bot. This holds the position of the
    ``Bot`` inside the Maze, its initial position, which team it belongs to
    etc..

`pelita.datamodel.Team`:
    In capture-the-flag each ``Bot`` belongs to a ``Team``. The team stores the
    homezone of a team and its score.

`pelita.datamodel.Maze`:
    Data structure that stores the maze or layout, i.e. where walls are.

`pelita.game_master.GameMaster`:
    Controller object that asks players for moves and updates the ``Universe``.
    You will never need to interact with this object but it's good to know that
    this is the central object that coordinates the game.

In addition to these classes there are two additional relevant concepts:

:``Player``:
    Your implementation of the *intelligence* for a ``Bot``. The abstraction is
    that a *player* object controls a *bot* object.

:``move``:
    A tuple that indicates where a ``Bot`` should move.

Player Basics
=============

In order to write a player you should subclass from
`pelita.player.AbstractPlayer`. This is an abstract class which provides
several convenience methods and properties to interrogate the universe
including the bot instance that this player controls, but lacks the functions
to actually control the bot.

To subclass from ``AbstractPlayer`` import this with::

    from pelita.player import AbstractPlayer

In order to make your player do something useful you must implement at least the
method ``get_move()`` to return a move. This can be one of::

    [north, south, west, east, stop]

The moves are provided by the `pelita.datamodel`, import them with::

    from pelita.datamodel import north, south, west, east, stop

An example of such a player is the trivial `pelita.player.StoppingPlayer`
which simply returns ``stop``:

.. literalinclude:: ../../pelita/player.py
   :pyobject: StoppingPlayer

.. note::

    Besides the definition of your player, this file must contain a factory
    function that returns a team (remember that the default game is a
    fight between two teams of two bots each)::

        def factory():
            return SimpleTeam("MyTeam", StoppingPlayer(), StoppingPlayer())

    For more information about this, see also::doc:`running_player`

Note: the current state or the ``CTFUniverse`` is always implicitly available
via the ``current_uni`` property inherited from ``AbstractPlayer``. But more
about that later.

Doing More
==========

A slightly more useful example is the `pelita.player.RandomPlayer` which always
selects a move at random from the possible moves:

.. literalinclude:: ../../players/RandomPlayers.py
   :pyobject: RandomPlayer

.. warning::

    In the above example, we use an internal random number generator,
    `self.rnd` instead of the one from the `random` module.

    `self.rnd` is seeded by the `GameMaster` during startup. This means
    that whenever we initialise `GameMaster` with the same seed, we will get
    the same numbers in our Player. This is very useful for testing,
    especially when playing against other Players which use randomness,
    because we can replay previous test games with improved algorithms.

.. note::

    To make the above example (and many of the following examples) work, it
    might be necessary to add appropriate imports to your python source file,
    for example::

        from pelita.player import AbstractPlayer
        from pelita.datamodel import north, south, west, east, stop

Here we can see the first convenience property ``legal_moves`` which returns a
dictionary mapping move tuples to position tuples. The random player simply
selects a move at random from the keys (moves) of this dictionary and then
moves there. ``legal_moves`` always includes stop.

The next example is the not-quite random player
``pelita.player.NQRandomPlayer``.  This one does not move back to the position
where it was on its last turn and never stops in place:

.. literalinclude:: ../../players/RandomPlayers.py
   :pyobject: NQRandomPlayer

Here we can see the use of another convenience method: ``previous_pos`` which
gives the position the bot had in the previous round.

Additional information about the bot and game state can also be retrieved
with the ``current_state`` dictionary.

The Maze Coordinate System
==========================

The coordinate system is the standard coordinate system used in computer games.
``x`` increases to the right, and ``y`` increases downwards, and a position is
encoded as the tuple ``(x, y)``. There are no negative coordinates. The
following example illustrates this for a few positions:

    +---------+---------+---------+---------+---------+
    | (0, 0)  | (1, 0)  | (2, 0)  | (3, 0)  | ...     |
    +---------+---------+---------+---------+---------+
    | (0, 1)  | (1, 1)  | (2, 1)  | (3, 1)  | ...     |
    +---------+---------+---------+---------+---------+
    | (0, 2)  | (1, 2)  | (2, 2)  | (3, 2)  | ...     |
    +---------+---------+---------+---------+---------+
    | ...     | ...     | ...     | ...     | ...     |
    +---------+---------+---------+---------+---------+

As a result we obtain the following direction vectors::

    north = (0, -1)
    south = (0, 1)
    west  = (-1, 0)
    east  = (1, 0)
    stop  = (0, 0)

Distances in the Maze
---------------------

There are different ways of measuring distances between objects in the maze.
The `Euclidean distance <https://en.wikipedia.org/wiki/Euclidean_distance>`_
is the length of the vector connecting the centers
of the cells where the objects are located:

.. figure:: images/distance_euclidean.png
   :alt: Euclidean distance.
   :width: 252px

   **Euclidean distance:** The Euclidean distance between the two bots is
   :math:`\sqrt{(x_1-x_2)^2 + (y_1-y_2)^2} = \sqrt{2^2+2^2} = \sqrt 8 \approx 2.83...`

The `Manhattan distance <https://en.wikipedia.org/wiki/Taxicab_geometry>`_,
also known as L1-distance or taxicab-distance, is the
absolute difference of the coordinates of the two objects:

.. figure:: images/distance_manhattan.png
   :alt: Manhattan distance.
   :width: 252px

   **Manhattan distance:** The Manhattan distance between the two bots is :math:`4`.

The maze distance counts the number of cells of the shortest path that
connects the two objects:

.. figure:: images/distance_maze.png
   :alt: Maze distance.
   :width: 252px

   **Maze distance:** The Maze distance between the two bots is :math:`6`.

Note that Manhattan and maze distances are always integer values.
In the game, distances are almost always measured either in Manhattan or in
maze distance.
We provide a series of convenience methods for dealing with position
and distances in `pelita.graph`:

.. currentmodule:: pelita.graph

.. autosummary::
   :nosignatures:

    move_pos
    diff_pos
    manhattan_dist

Recovery Strategies in Case of Death or Timeout
-----------------------------------------------

Lastly, we are going to see some error recovery code in the
``get_move()`` method.

As it happens, an offensive player can get killed every now and then. In
order to detect this, it's best to compare the current position with its
initial position using the ``initial_pos`` convenience property, since this is
where it will respawn. Alternatively, it is also possible to keep track of the
timeouts using ``self.current_state["timeout_teams"]``, which holds the
number of timeouts each team has already used up.

Your player only has a limited time to return from ``get_move()``. The default
is approximately three seconds. If your player does not respond in time, the
``GameMaster`` will move the bot at random for this turn. It's important to
recover from such an event.

The main problem with detecting a timeout is that, as long as your
computationally expensive process is running, there is no way to interrupt it.
Imagine an infinite ``for`` loop in your ``get_move()``::

    while True:
        pass

In this case, your ``get_move()`` will be executed exactly once! Thus it is
important to ensure that your search algorithms are efficient and fast.

For convenience ``AbstractPlayer`` has a ``time_spent()`` method, which
shows the approximate time since ``get_move()`` has been called. A simple
approach using this method could be as follows::

    def get_move():
        self.best_move = stop
        MAX_TIME = 3 # whatever the rules tell you
        if self.time_spent() > MAX_TIME - 0.5:
            return self.best_move
        # do some iterative data mining and eventually
        # change the value of self.best_move
        self.do_first_calculation()
        if self.time_spent() > MAX_TIME - 0.5:
            return self.best_move
        self.do_second_calculation()
        # ...


.. note::

    Even though ``time_spent()`` takes into account the initial calculations
    done in ``AbstractPlayer``, it knows nothing about network delays.
    Therefore, it seems adviseable not to wait until the last millisecond
    before returning.

A very important thing to emphasise is the following: When one bot blocks,
the whole team blocks. This means that all subsequent calls to ``get_move()``
for a team are stalled until the blocking ``get_move()`` has finished.

This also means, that it may happen that the second call to ``get_move()``
is already behind in terms of time when it is being executed. In extreme
cases, it may even generate a second timeout *before* its execution.

There is no good way to predict this other than keeping track of one’s
own execution time and returning early, if necessary. For long lasting
tasks, it may be a good idea to experiment with concurrency.

.. note::

    A remark on timeout handling during the ``set_initial()`` phase.

    Sometimes, it may seem a good idea to do some pre-calculations during the
    ``set_initial`` phase. We like to enforce this by also giving each Player
    some extra time. There is no strict limit, but after three seconds, the
    ``GameMaster`` is going to move on with its duty. Just make sure you’ll be
    ready when you receive the first ``get_move()`` call.


.. TODO: maybe prepare some graphics for the duplicate timeouts situation
.. TODO: the universe states will be missing a state


Interacting with the Maze
=========================

For a simple test whether a certain position on the maze is free or not,
we can check the ``pelita.datamodel.Maze`` class which has an instance in
our universe.::

    pos = (3, 3)
    if maze[pos]:
        # has a wall
    else:
        # is free

.. note::

    Please compare the above syntax with::

        pos = (3, 3)
        if pos in maze:
            pass

    This checks whether a coordinate is valid.


Players may use an adjacency list representation provided by
``pelita.graph.AdjacencyList``. Let's have a quick look at how this is
generated, in case you would like to implement your own `graph storage
<https://en.wikipedia.org/wiki/Graph_(data_structure)>`_ or leverage an
alternative existing package such as `NetworkX <https://networkx.github.io>`_.

In order to obtain the positions of all free spaces, the
``pelita.datamodel.CTFUniverse`` class provides the method
``pelita.datamodel.CTFUniverse.free_positions()``.

There are a few additional constructs that are
useful when dealing with the maze. The property ``positions`` gives all the
positions in the maze.


Noisy Enemy Positions
=====================

In general, the ``CTFUniverse`` you receive is noisy. This means that you can
only obtain an accurate fix on the enemy bots if they are within 5 squares of
manhattan distance. Otherwise, the position is noisy with a uniform radius of
5 squares manhattan distance. These two values may lead to confusing values:
for example if the bot is 6 squares away, but the added noise of 4 squares
towards your bot, make it appear as if it were only 2 squares away.
Thus, you can check if a bot position is noisy using the ``noisy`` attribute
of the bot instance, in combination with the ``enemy_bots`` convenience property
provided by ``AbstractPlayer``::

    self.enemy_bots[0].noisy

One idea is to implement probabilistic tracking using a `Kalman filter
<https://en.wikipedia.org/wiki/Kalman_filter>`_

If you wish to know how the noise is implemented, look at the class:
``pelita.game_master.UniverseNoiser``.

As a special note regarding the ``ManhattanNoiser`` that is being used: All noised
positions are still going to be valid free positions inside the maze. That is, the
noiser will not return a position that has a wall. It may however return an impossible
game situation in that a bot may show as sitting upon a food item without eating it.

Implementation Details of Convenience Properties
================================================

This section contains some details about the implementation of the convenience
properties of ``AbstractPlayer``. Reading this section is not required, but may
be of interest to the curious reader.

Let's take a quick look as the implementation
of ``current_uni``:

.. literalinclude:: ../../pelita/player.py
   :pyobject: AbstractPlayer.current_uni

Importantly we see that the ``AbstractPlayer`` automatically maintains a stack
of previous states of the Universe called ``universe_states``.
As we can see ``current_uni`` is simply the top element of this stack. This
allows us to access the properties and methods of the ``CTFUniverse``, for
example look at the implementation of ``legal_moves``:

.. literalinclude:: ../../pelita/player.py
   :pyobject: AbstractPlayer.legal_moves

Here we can see that this simply calls the method ``legal_moves(pos)``
which is provided by ``CTFUniverse``. We also see one of the convenience
properties used in the ``bfs_food()`` method: ``current_pos`` which returns the
current position of the bot.  Let's have a look at this:

.. literalinclude:: ../../pelita/player.py
   :pyobject: AbstractPlayer.current_pos

We see that this makes use of the ``me`` property which is defined as follows:

.. literalinclude:: ../../pelita/player.py
   :pyobject: AbstractPlayer.me

As you can see, ``me`` will simply obtain the ``Bot`` instance controlled by
this player from the current universe using the hidden ``_index`` attribute of
the player. In practice, you should be able to avoid having to use the
``_index`` directly but it's good to know how this is implemented in case you
wish to do something exotic.

Lets now have a look at the convenience property ``enemy_food`` Again, this is
simply forwarded to the ``CTFUniverse`` using ``current_uni``:

.. literalinclude:: ../../pelita/player.py
   :pyobject: AbstractPlayer.enemy_food

As with ``legal_moves``, a method from ``CTFUniverse`` is called, namely
``enemy_food``. However, we need to tell it which team we are on. This is
obtained using the ``me`` property to access the controlled ``Bot`` instance,
which in turn stores the ``team_index``. In practice, the information stored in
the ``CTFUniverse`` should be accessible through the convenience properties of
the ``AbstractPlayer``. However, if these do not suffice, please have a look
at the source code.

Now that you know about ``universe_states``, ``_index`` and ``current_pos``
let's have a look at how the ``previous_pos`` property (used in the
``NQRandomPlayer``) is implemented:

.. literalinclude:: ../../pelita/player.py
   :pyobject: AbstractPlayer.previous_pos

Again, we will make use of ``universe_states``, but this time we will look at
the second element from the top of the stack. The ``CTFUniverse`` maintains a
list of bots ``bots`` and the hidden attribute ``_index`` can be used to obtain
the respective bot instance controlled by the player. Lastly, we simply look at
the ``current_pos`` property of the bot (the bot instance from one turn ago) to
obtain its previous position.

The ``team`` property uses the ``me`` property to access the bots
``team_index`` which it then uses in ``current_uni.teams`` to get the
respective ``Team`` instance:

.. literalinclude:: ../../pelita/player.py
   :pyobject: AbstractPlayer.team

Something similar is achieved for the ``team_border``:

.. literalinclude:: ../../pelita/player.py
   :pyobject: AbstractPlayer.team_border

And again for ``enemy_bots``:

.. literalinclude:: ../../pelita/player.py
   :pyobject: AbstractPlayer.enemy_bots
