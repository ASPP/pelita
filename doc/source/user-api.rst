.. _user_api_reference:

==================
User API Reference
==================

This section summarizes the modules, classes and functions that are relevant
when writing a player.

.. currentmodule:: pelita.player.AbstractPlayer

Convenience Properties of ``AbstractPlayer``
--------------------------------------------

.. rubric:: Basic Properties

.. autosummary::

    current_uni
    current_state
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
    team_food

.. rubric:: Enemy Properties

.. autosummary::

    enemy_team
    enemy_bots
    enemy_food

Example Players
---------------

.. currentmodule:: pelita.player

.. autosummary::

    StoppingPlayer

.. currentmodule:: players

.. autosummary::

    RandomPlayer
    NQRandomPlayer
    SmartRandomPlayer
    RandomExplorerPlayer
    FoodEatingPlayer

Accessing ``pelita.datamodel``
------------------------------

.. currentmodule:: pelita.datamodel

.. rubric:: Important Classes

.. autosummary::

    CTFUniverse
    Bot
    Team
    Maze

.. rubric:: Maze components

.. autosummary::

    Wall
    Free
    Food

Helper functions in ``pelita.graph``
------------------------------------

.. currentmodule:: pelita.graph

.. rubric:: Convenience Functions

.. autosummary::

    new_pos
    diff_pos
    manhattan_dist

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
    enemy_team
    enemy_bots
    enemy_food
    legal_moves
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
