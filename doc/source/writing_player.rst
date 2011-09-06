================
Writing a Player
================

This section explains how to write a Player.

.. contents::

Player Basics
=============

In order to write a Player you should subclass from
``pelita.player.AbstractPlayer``. This is an abstract class which provides
several convenience methods to interrogate the Universe including the Bot
instance that this player controls but lacks the functions to actually control
the Bot.

To subclass from ``AbstractPlayer`` import this with::

    from pelita.player import AbstractPlayer

In order to make your Player do something useful you must implement at least the
method ``get_move(self)`` to return a move. This can be one of::

    (north, south, west, east, stop)

The moves are provided by the ``pelita.datamodel``, import them with::

    from pelita.datamodel import north, south, west, east, stop

An example of such a player is the trivial ``pelita.players.StoppingPlayer``
which simply returns ``stop``:

.. literalinclude:: ../../pelita/player.py
   :pyobject: StoppingPlayer

Where to place you files
========================

To begin using your own Player you need to create a startup script similar to
``demo.py`` and execute this using the `PYTHONPATH
<http://docs.python.org/using/cmdline.html#envvar-PYTHONPATH>`_ environment
variable.

First create an empty directory outside the pelita source code directory, and
make some empty files::

    $ cd ~
    $ mkdir my_agent
    $ cd my_agent
    $ touch my_agent.py
    $ touch run_game.py

You can then implement you player in the file ``my_player.py``, for example:

.. literalinclude:: my_player/my_player.py
   :language: python

The next thing you need is a python script to run your player. Implement this in
``my_game.py`` using classes from the ``pelita.simplesetup`` module:

.. literalinclude:: my_player/my_game.py
   :language: python

Now to run the game you need to use the ``PYTHONPATH`` to point to the pelita
source code. Assuming this is in ``$HOME/pelita`` you can execute
``my_game.py`` using::

    $ PYTHONPATH=$HOME/pelita python my_game.py

Now that you are set up, read the next section on how to make you Player do
something useful :-).


Doing More
==========

A slightly more useful example is the ``RandomPlayer`` which always selects a
move at random from the possible moves:

.. literalinclude:: ../../pelita/player.py
   :pyobject: RandomPlayer

Here we can see the first convenience method: ``legal_moves`` which returns a
dictionary mapping move tuples to position tuples. The random player simply
selects a move at random from the keys (moves) of this dictionary and then moves
there. ``legal_moves`` always includes stop.

The next example if the not-quite random Player ``NQRandomPlayer``. This ones
does not move back to the position where it was on its last turn and does not
ever stop in place:


.. literalinclude:: ../../pelita/player.py
   :pyobject: NQRandomPlayer

Here we can see the use of another convenience method: ``previous_pos`` which
gives the position the Bot had in the previous round. Lets take a closer look at
how this is implemented:

.. literalinclude:: ../../pelita/player.py
   :pyobject: AbstractPlayer.previous_pos

Importantly we see that the ``AbstractPlayer`` automatically maintains a stack
of previous states of the Universe called ``universe_states``. Here we look at
the previous state and obtain the bots positions. The Universe maintains a list
of Bots ``bots`` and each Player has an attribute ``_index`` which can be used
to obtain the respective Bot instance controlled by the Player. Lastly we simply
look at the ``current_pos`` property of the Bot to obtain the previous position.

The Maze Coordinate System
==========================

The coordinate system is the standard coordinate system used in computer games.
``x`` increases to the left, and ``y`` increases downwards, and a position is
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

A Basic Offensive Player
========================

A somewhat more elaborate example is the ``BFSPlayer`` which uses *breadth first
search* to find food:

.. literalinclude:: ../../pelita/player.py
   :pyobject: BFSPlayer

Here we can already see some more advanced concepts. The first thing to note is
that any player can override the method ``set_initial(self)`` where
``current_uni`` is the starting state of the game. All food is still present and
all Bots are at their initial position. In this method we initialise the
adjacency list representation of the maze. Lets look as the implementation of
``current_uni``:



.. literalinclude:: ../../pelita/player.py
   :pyobject: AbstractPlayer.current_uni

As we can see it's simply the top element on the ``universe_states`` stack
mentioned earlier. In order to obtain the positions of all ``Free`` the Universe
provides a method ``pos_of(maze_component)`` which will return the positions of
all ``MazeComponent`` type objects. We then use the method
``get_legal_moves(self,pos)`` for each of the free positions to build the
adjacency list.

The breadth first search is implemented in the method ``bfs_food`` which returns
a path to closest food element. In this method we see some more convenience, for
example ``enemy_food`` which returns a list of all food that we can eat. One of
the convenience properties used here is ``current_pos`` which returns the
current position. Let have a look at this:

.. literalinclude:: ../../pelita/player.py
   :pyobject: AbstractPlayer.current_pos

We see that this makes use of the ``me`` property which is defined as follows:

.. literalinclude:: ../../pelita/player.py
   :pyobject: AbstractPlayer.me

As you can see ``me`` will simply obtain the Bot instance controlled by this
player from the current universe using the hidden ``_index`` attribute of the
Player. In practice you should be able to avoid having to use the
``_index`` directly but it's good to know how this is implemented in case you
wish to do something exotic.

Noisy Enemy Positions
=====================

In general, the ``CTFUniverse`` you receive is noisy. This means that you can
only obtain an accurate fix on the enemy bots if they are within 5 squares maze
distance. Otherwise the position is noisy with a uniform radius of 5 squares
maze distance. These two values may lead to confusing values: for example if the
Bot is 6 squares away, but the added noise of 4 squares towards your Bot, make
it appear as if it were only 2 squares away. Thus, you can check if a Bot
position is noisy using the ``noisy`` attribute of the Bot instance::

    self.enemy_bots[0].noisy

One idea is to implement probabilistic tracking using a `Kalman filter
<http://en.wikipedia.org/wiki/Kalman_filter>`_

If you wish to know how the noise is implemented look at the class:
``pelita.game_master.UniverseNoiser``.

A Basic Defensive Player
========================

As a defensive example we have the ``BasicDefensePlayer``:

.. literalinclude:: ../../pelita/player.py
   :pyobject: BasicDefensePlayer

All example Players can be found in the module ``pelita.player``.


Source Code for ``pelita.player.AbstractPlayer``
================================================

Below is the complete code for the ``AbstractPlayer`` which shows you all of the
convenience methods/properties and also some of the implementation details:

.. literalinclude:: ../../pelita/player.py
   :pyobject: AbstractPlayer

Glossary
========

:``Universe``:
    The game state.

:``Bot``:
    The datastructure used to store the agent.

:``Team``:
    In capture-the-flag each ``Bot`` belongs to a ``Team``.

:``Player``:
    Your implementation of the *intelligence* for a ``Bot``.

:``Mesh``:
    A two-dimensional container mapping a position tuple to an object.

:``Maze``:
    Datastructure that stores the maze.

:``MazeComponent``:
    Classes storing the characters used in the ``Maze``.

:``GameMaster``:
    Controller object that asks players for moves and updates the ``Universe``.

:``Move``:
    A tuple that indicates where a ``Bot`` should move.

The connections are as follows: A ``Universe`` contains a list of ``Bot``
objects, a list of ``Team`` objects and a ``Maze`` object. The ``Maze`` object
is implemented with a ``Mesh``. At each position, a multi-character string that
encodes the type of ``MazeComponents`` stored at that position. The classes
derived from ``MazeComponent``: ``Free``, ``Wall`` and ``Food`` store the
mapping of single character to ``MazeComponent``.  A ``Player``
implements/controls the logic required to navigate a ``Bot``. The ``GameMaster``
will forward the current state of the ``Universe`` to the ``Player`` and request
a ``Move`` in return. Upon receipt of the next ``Move`` the ``GameMaster`` will
update the ``Universe``.
