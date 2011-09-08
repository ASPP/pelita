================
Writing a Player
================

This section explains how to write a player.

.. contents::

Introduction
============

To begin with, we must define a few classes and some terminology which will be
used throughout this documentation.

:``pelita.datamodel.CTFUniverse``:
    The game state. Holds a list of ``Bot`` instances, a list of ``Team``
    instances and a single ``Maze`` object. Can be queried to obtain
    information about the game.

:``pelita.datamodel.Bot``:
    The data structure used to store the bot. This holds the position of the
    ``Bot`` inside the Maze, its initial position, which team it belongs to
    etc..

:``pelita.datamodel.Team``:
    In capture-the-flag each ``Bot`` belongs to a ``Team``. The team stores the
    indices of its bot, the score, the team name etc..

:``pelita.datamodel.Maze``:
    Data structure that stores the maze or layout, i.e. where walls and food
    are.

:``pelita.game_master.GameMaster``:
    Controller object that asks players for moves and updates the ``Universe``.
    You will never need to interact with this object but its good to know that
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
``pelita.player.AbstractPlayer``. This is an abstract class which provides
several convenience methods and properties to interrogate the universe including
the bot instance that this player controls, but lacks the functions to actually
control the bot.

To subclass from ``AbstractPlayer`` import this with::

    from pelita.player import AbstractPlayer

In order to make your player do something useful you must implement at least the
method ``get_move(self)`` to return a move. This can be one of::

    (north, south, west, east, stop)

The moves are provided by the ``pelita.datamodel``, import them with::

    from pelita.datamodel import north, south, west, east, stop

An example of such a player is the trivial ``pelita.players.StoppingPlayer``
which simply returns ``stop``:

.. literalinclude:: ../../pelita/player.py
   :pyobject: StoppingPlayer

Note: the current state or the ``CTFUniverse`` is always implicitly available
via the ``current_uni`` property inherited from ``AbstractPlayer``. But more
about that later.

Where to place you files
========================

To begin using your own player you need to create a startup script similar to
``demo.py`` and execute this using the `PYTHONPATH
<http://docs.python.org/using/cmdline.html#envvar-PYTHONPATH>`_ environment
variable.

First create an empty directory outside the Pelita source code directory, and
make some empty files::

    $ cd ~
    $ mkdir my_agent
    $ cd my_agent
    $ touch my_agent.py
    $ touch run_game.py

You can then implement you player in the file ``my_player.py``, for example:

.. literalinclude:: my_player/my_player.py

The next thing you need is a python script to run your player. Implement this in
``my_game.py`` using classes ``SimpleServer`` and ``SimpleClient`` from the
``pelita.simplesetup`` module and also ``SimpleTeam`` from ``pelita.player``:

.. literalinclude:: my_player/my_game.py

Now to run the game you need to use the ``PYTHONPATH`` to point to the Pelita
source code. Assuming this is in ``$HOME/pelita`` you can execute
``my_game.py`` using::

    $ PYTHONPATH=$HOME/pelita python my_game.py

If instead of the TkInter based display, you would like to use a text-mode
output replace ``server.run_tk()`` with::

    server.run_ascii()

If you wish to play a shorter game use the ``rounds=N`` keyword argument for
``SimpleServer``::

    SimpleServer(rounds=100)

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

The next example is the not-quite random player ``NQRandomPlayer``. This ones
does not move back to the position where it was on its last turn and does not
ever stop in place:


.. literalinclude:: ../../pelita/player.py
   :pyobject: NQRandomPlayer

Here we can see the use of another convenience method: ``previous_pos`` which
gives the position the bot had in the previous round.

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

We provide a series of convenience methods for dealing with position tuples in
``pelita.datamodel``:

:``new_pos``: Adds a position tuple and a move tuple.
:``diff_pos``: Return the move required to move from one position to another.
:``is_adjacent``: Check that two positions are adjacent.
:``manhattan_dist``: Manhattan distance between two points.

Loading Alternative Mazes
=========================

By default ``SimpleServer`` will load a random maze for four players. There are
three possible keyword arguments which you may use to select a specific layout:
``layout_string``, ``layout_name`` and ``layout_file``. If you specify more than
one of these, ``SimpleServer`` will complain.

``layout_string``
-----------------

Using ``layout_string`` allows you to embed the maze layout as a string directly
into your code:

.. literalinclude:: my_player/my_game_layout_string.py
   :lines: 18-37

As you can see from the example, only a few characters are needed to encode a
maze:

:``'#'``:
    wall
:``' '``:
    free space
:``'.'``:
    food

And in addition, integers specify the starting position of each bot. In the
above example ``0`` and ``2`` are on the team on the left and ``1`` and ``3``
are on the team on the right.  There are some restrictions on the encoding
however:

* The maze must be rectangular and even in the x-direction.
* It must be fully enclosed by walls.
* No illegal characters can be used.

By default a four-bot maze is expected (integers ``0-3`` must be present. If you
wish to play with two bots instead, pass ``players=N`` as keyword argument to
the ``SimpleServer``::

    SimpleServer(players=2)

Any leading or trailing whitespace will be stripped. The layout will be
parsed for correctness. and will raise an exception if any errors are detected.

This feature should give you enough flexibility to run smallish test games.

``layout_name``
---------------

Using ``layout_name`` and  you can use any of the mazes provided. The mazes are
stored in the ``layouts`` directory and there is some magic to load them into
the Pelita name space.

The filenames in layouts in the ``layouts`` have the ``.layout`` extension::

    $ cd layouts
    $ ls | head
    01_demo.layout
    01_with_dead_ends.layout
    01_without_dead_ends.layout
    02_demo.layout
    02_with_dead_ends.layout
    02_without_dead_ends.layout
    03_demo.layout
    03_with_dead_ends.layout
    03_without_dead_ends.layout
    04_demo.layout

To have them available in the Pelita name space we make them available from the
auto generated module ``pelita.__layouts`` module. When converting from
filenames to variable names we prefix the layout name with the string
``layout_`` and remove the ``.layout`` extension (because variables in Python
can not begin with a number). Thus the layout stored in the file
``01_demo.layout`` becomes ``layout_01_demo``, ``18_with_dead_ends.layout``
becomes ``layout_18_with_dead_ends`` and so on.

You can get them using: ``pelita.layout.get_layout_by_name``::

    >>> from pelita.layout import get_layout_by_name
    >>> print get_layout_by_name('layout_01_demo')
    ################################
    #   #. #.#.#       #     #.#.#3#
    # # ##       ##  #   ###   #.#1#
    # # #. # ###    #### .#..# # # #
    # # ## # ..# #   #   ##### # # #
    # #    ##### ###   ###.#   # # #
    # ## # ..#.  #.###       #   # #
    # #. ##.####        #.####  ## #
    # ##  ####.#        ####.## .# #
    # #   #       ###.#  .#.. # ## #
    # # #   #.###   ### #####    # #
    # # # #####   #   # #.. # ## # #
    # # # #..#. ####    ### # .# # #
    #0#.#   ###   #  ##       ## # #
    #2#.#.#     #       #.#.# .#   #
    ################################

You can look at the available names using ``pelita.get_available_layouts``::

    >>> from pelita.layout import get_available_layouts
    >>> for layout_name in get_available_layouts()[:10]:
    ...     print layout_name
    ...
    layout_01_demo
    layout_01_with_dead_ends
    layout_01_without_dead_ends
    layout_02_demo
    layout_02_with_dead_ends
    layout_02_without_dead_ends
    layout_03_demo
    layout_03_with_dead_ends
    layout_03_without_dead_ends
    layout_04_demo

Once you have found a layout you like, pass the desired layout name to the
``SimpleServer`` using the ``layout_name`` keyword argument:

.. literalinclude:: my_player/my_game_layout_name.py
   :lines: 18-19

``layout_file``
---------------

Lastly you can use the ``layout_file`` keyword argument to load a layout
from a given file.  Assuming you have a file ``my_layout.layout`` which
contains:

.. literalinclude:: my_player/my_layout.layout

...you would use:

.. literalinclude:: my_player/my_game_layout_file.py
   :lines: 18-19

A Basic Offensive Player
========================

A somewhat more elaborate example is the ``BFSPlayer`` which uses *breadth first
search* on an *adjacency list* representation of the maze to find food:

.. literalinclude:: ../../pelita/player.py
   :pyobject: BFSPlayer

Here we can already see some more advanced concepts. The first thing to note is
that any player can override the method ``set_initial(self)``. All food is still
present and all bots are at their initial position. In this method we initialise
the adjacency list representation of the maze. As mentioned previously the
current state of the universe is always available as ``current_uni``. Within
``set_initial(self)`` this is the starting state.

Lets take a quick look as the implementation
of ``current_uni``:

.. literalinclude:: ../../pelita/player.py
   :pyobject: AbstractPlayer.current_uni

Importantly we see that the ``AbstractPlayer`` automatically maintains a stack
of previous states of the Universe called ``universe_states``.
As we can see ``current_uni`` is simply the top element of this stack.

Further convenience properties used in the ``bfs_food()`` method are
``current_pos`` which returns the current position of the bot, and
``enemy_food`` which returns a list of position tuples of the food owned by the
enemy (which can be eaten by this bot). Let have a look at ``current_pos``:

.. literalinclude:: ../../pelita/player.py
   :pyobject: AbstractPlayer.current_pos

We see that this makes use of the ``me`` property which is defined as follows:

.. literalinclude:: ../../pelita/player.py
   :pyobject: AbstractPlayer.me

As you can see ``me`` will simply obtain the bot instance controlled by this
player from the current universe using the hidden ``_index`` attribute of the
player. In practice you should be able to avoid having to use the
``_index`` directly but it's good to know how this is implemented in case you
wish to do something exotic.

Now that you know about ``universe_states``, ``_index`` and ``current_pos`` lets
look at how the ``previous_pos`` property used in the ``NQRandomPlayer`` is
implemented:

.. literalinclude:: ../../pelita/player.py
   :pyobject: AbstractPlayer.previous_pos

Again we access ``universe_states``, but this time we look at the second element
from the top of the stack. The Universe maintains a list of bots ``bots`` and
the hidden attribute ``_index`` can be used to obtain the respective bot
instance controlled by the player. Lastly we simply look at the ``current_pos``
property of the bot (the bot instance from one turn ago) to obtain its previous
position.

There are a few more convenience properties available from
``AbstractPlayer``, you should look at the section `Source Code for
AbstractPlayer`_ for details.

In order to obtain the positions of all ``Free`` the Universe
provides a method ``pos_of(maze_component)`` which will return the positions of
all ``MazeComponent`` type objects. We then use the method
``get_legal_moves(self,pos)`` for each of the free positions to build the
adjacency list.

Noisy Enemy Positions
=====================

In general, the ``CTFUniverse`` you receive is noisy. This means that you can
only obtain an accurate fix on the enemy bots if they are within 5 squares maze
distance. Otherwise the position is noisy with a uniform radius of 5 squares
maze distance. These two values may lead to confusing values: for example if the
bot is 6 squares away, but the added noise of 4 squares towards your bot, make
it appear as if it were only 2 squares away. Thus, you can check if a bot
position is noisy using the ``noisy`` attribute of the bot instance::

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


Source Code for ``AbstractPlayer``
================================================

Below is the complete code for the ``pelita.player.AbstractPlayer`` which shows
you all of the convenience methods/properties and also some of the
implementation details:

.. literalinclude:: ../../pelita/player.py
   :pyobject: AbstractPlayer

