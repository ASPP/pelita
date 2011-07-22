======================
Introduction to Pelita
======================

Autonomous agent environment in Python

Glossary
========

:Universe:
    The game state.

:Bot:
    The datastructure used to store the agent.

:Team:
    In capture-the-flag each Bot belongs to a Team.

:Player:
    Your implementation of the *intelligence* for a Bot.

:Mesh:
    A two-dimensional container mapping a position tuple to an object.

:Maze:
    Datastructre that stores the maze.

:Move:
    A tuple that indicates where a Bot should move.

Writing a Player
================

In order to write a Player you should subclass from
`pelita.player.AbstractPlayer`. This is an abstract class which provides several
convenience methods to interrogate the Universe including the Bot instance that this
player controls but lacks the functions to actually control the Bot. In order to
make your Player do something useful you must implement at least the method
`get_move(self, universe)` to return a move. This can be one of:

.. literalinclude:: ../../pelita/datamodel.py
   :lines: 8-12

The moves are provided by the `datamodel`, import them with::

    from pelita.datamodel import north, south, west, east, stop

An example of such a player is the trivial `StoppingPlayer` which simply returns
`stop`:

.. literalinclude:: ../../pelita/player.py
   :pyobject: StoppingPlayer

A slightly more useful example is the `RandomPlayer` which always selects a move
at random from the possible moves:

.. literalinclude:: ../../pelita/player.py
   :pyobject: RandomPlayer

TODO : describe how get_legal_moves works

TODO : NQRPlayer

A somewhat more elaborate example is the `BFSPlayer` which uses breadth first
search to find food:

.. literalinclude:: ../../pelita/player.py
   :pyobject: BFSPlayer

Here we can already see some more advanced concepts. The first thing to note is
that any player can override the method `set_initial(self)` where `current_uni`
is the starting state of the game. All food is still present and all Bots are at
their initial position. In this method we initialise the adjacency list
representation of the maze.

TODO : more description of this player

All example Players can be found in the module `pelita.player`.

Git-Repository
==============

The official Git-Repository is hosted at Github:
`https://github.com/Debilski/pelita <https://github.com/Debilski/pelita>`_

You can create a clone with::

    $ git clone git://github.com/Debilski/pelita.git
