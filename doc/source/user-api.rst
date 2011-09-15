==================
User API reference
==================

.. default-role:: py:obj

This section summarizes the modules, classes and functions that are relevant
when writing a player.

.. contents::

.. currentmodule:: pelita.player.AbstractPlayer

Convenience Properties of ``AbstractPlayer``
--------------------------------------------

.. rubric:: Basic properties

.. autosummary::

    current_uni
    me
    team
    legal_moves

.. rubric:: Positional Properties

.. autosummary::

    initial_pos
    current_pos
    previous_pos

.. rubric:: Team Properties

.. autosummary::

    team_border
    team_bots
    other_team_bots

.. rubric:: Enemy Properties

.. autosummary::

    enemy_bots
    enemy_food

Example Players
---------------

.. currentmodule:: pelita.player

.. autosummary::

    StoppingPlayer
    RandomPlayer
    NQRandomPlayer
    BFSPlayer
    BasicDefensePlayer

Accessing ``pelita.datamodel``
------------------------------

.. currentmodule:: pelita.datamodel

.. rubric:: Convenience Functions

.. autosummary::

    diff_pos
    is_adjacent
    manhattan_dist
    new_pos

.. rubric:: Important Classes

.. autosummary::

    CTFUniverse
    Bot
    Team
    Maze

.. rubric:: MazeComponents

.. autosummary::

    MazeComponent
    Wall
    Free
    Food

Interfacing with the ``CTFUniverse``
------------------------------------

.. rubric:: Attributes

+---------+----------------------------------------------+
| maze    | instance of `pelita.datamodel.Maze`          |
+---------+----------------------------------------------+
| teams   | list of instances of `pelita.datamodel.Team` |
+---------+----------------------------------------------+
| bots    | list of instances of `pelita.datamodel.Bot`  |
+---------+----------------------------------------------+

.. currentmodule:: pelita.datamodel.CTFUniverse

.. rubric:: Convenience Properties and Functions

.. autosummary::

    bot_positions
    food_list
    pretty
    enemy_bots
    enemy_food
    get_legal_moves
    other_team_bots
    team_border
    team_bots
    team_food

Interfacing with the ``Maze``
-----------------------------

.. currentmodule:: pelita.datamodel.Maze

.. rubric:: Convenience Properties and Functions

.. autosummary::

    shape
    positions
    pos_of
