.. Pelita documentation master file, created by
   sphinx-quickstart on Mon Jul 18 14:32:16 2011.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.
======
Pelita
======

.. figure:: images/demogame.png
   :alt: Screenshot.

   **A first fight:** 'the bad ones' VS. 'the good ones'

**Pelita** is an artificial intelligence programming game in Python, based
loosely on Pacman.

Description of the game
=======================

Two teams of one or more *bots* compete in a *maze* that is filled with *food*.
The maze is split into two parts, the left and the right half, where each team
*owns* one half of the maze.  Each bot can have one of two states, depending on
its position in the maze. In its own half the bot is a *destroyer* (equivalent to
a ghost). In the enemy half, the bot is a *harvester* (equivalent to a pacman). As
a destroyer a bot can *destroy* enemy harvesters in its own half. As a
harvester a bot can *eat* food that belongs to the enemy. The ultimate goal is
to eat all the enemy's food.

Your task as *user* is to implement one or more *players* to control bots. Your
players must implement the *intelligence* to navigate you bots successfully
through the maze, destroy the enemy's harvesters and eat the enemy's food.

Contents:

.. toctree::
   :maxdepth: 2

   writing_player
   development

Acknowledgements
================

This software was developed for the 'Advanced Scientific Programming in Python'
summer school, as a teaching aid for the group project.

Future:

* `St. Andrews, Scotland, 2011 <https://python.g-node.org/wiki/>`_

Past:

* `Trento, Italy, 2010 <https://python.g-node.org/python-autumnschool-2010/>`_
* `Warsaw, Poland, 2010 <http://escher.fuw.edu.pl/pythonschool/>`_
* `Berlin, Germany, 2009 <http://portal.g-node.org/python-summerschool-2009/>`_

Initial funding was kindly provided by `The German Neuroinformtaics Node
<http://www.g-node.org/>`_

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

