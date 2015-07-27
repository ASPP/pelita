======
Pelita
======

.. container:: container-fluid

   .. container:: row

      .. container:: col-md-6

         .. image:: images/small-game@2x.png
            :scale: 50%
            :alt: Screenshot.
            :class: img-responsive

         **A first fight:** ‘The SmartRandomPlayers’ v ‘The FoodEatingPlayers’

      .. container:: col-md-6

         .. literalinclude:: ../../players/SmartRandomPlayer.py
            :pyobject: SmartRandomPlayer

**Pelita** is Actor-based Toolkit for Interactive Language Education in Python.

Resources
=========
- `Documentation <http://aspp.github.com/pelita/>`_
- `Source code <https://github.com/ASPP/pelita>`_
- `Issue tracker <https://github.com/ASPP/pelita/issues>`_

Description of the Game
=======================

Two teams, of one or more *bots*, compete in a *maze* that is filled with *food*.
The maze is split into two parts, the left and the right half, where each team
*owns* one half of the maze.  Each bot can have one of two states, depending on
its position in the maze. In its own half, the bot is a *destroyer*. In the
enemy half, the bot is a *harvester*. As a destroyer, a bot can *destroy* enemy
harvesters in its own half. As a harvester, a bot can *eat* food that belongs to
the enemy. The ultimate goal is to eat all the enemy's food.

Your task as *user* is to implement one or more *players* to control bots. Your
players must implement the *intelligence* to navigate your bots successfully
through the maze, destroy the enemy's harvesters, and eat the enemy's food.


Quick Start
===========

First clone the source code repository::

    $ git clone http://github.com/ASPP/pelita.git

And launch the command-line interface::

    $ ~/pelita/pelitagame

This will start a demo game using the `TkInter
<http://wiki.python.org/moin/TkInter>`_ interface on a random maze
with some predefined players.

Continue reading: :ref:`writing_a_player`.

Contents
========

.. toctree::
   :hidden:

   info
   writing_player
   running_player
   development
   user-api
   api

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
