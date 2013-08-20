===============
Running Players
===============

To run a game using your player, you should use the command-line interface:
``pelitagame``. Run it with the ``--help`` option to get a detailed usage
description.


Where to Place Your Files
=========================

To begin using your own player you need to put its definition in a place
where ``pelitagame`` can find it.

Put the definition of your player in a file outside the Pelita source
code directory, for example in ``/home/student/my_player.py``. Besides
the definition of your player, this file must contain a factory
function that returns a team (remember that the default game is a
fight between two teams of two bots each):

.. literalinclude:: my_player/my_player.py

The factory function is used by the command-line program to lead your
players into the game.
To run a game using your players against some predefined players in
Pelita you can run ::

       $ ~/pelita/pelitagame /home/student/my_player.py BFSPlayer,BasicDefensePlayer

This setup is fine for small tests, but if you plan to have a more
complicated directory structure, for example to load additional
utilities located in different files, read on to section
`Tournament Setup`_.


Load Custom Layouts
===================

For testing purposes it may be useful to use small hand-crafted maze
layouts instead of the default big ones. You can easily define your
own layout in a file and load it into the game with::

   $ ~/pelita/pelitagame --layoutfile my_test_layout.txt /home/student/my_player.py BFSPlayer,BasicDefensePlayer

A layout file looks like this:

.. literalinclude:: my_player/my_test_layout.txt
   :language: text

As you can see from the example, only a few characters are needed to encode a
maze:

:``'#'``:
    wall
:``' '``:
    free space
:``'.'``:
    food

In addition, the starting position of each bot is specified by a number. In the
above example ``0`` and ``2`` are on the team on the left and ``1`` and ``3``
are on the team on the right.  There are some restrictions on the encoding
however:

* The maze must be rectangular and even in the x-direction.
* It must be fully enclosed by walls.
* No illegal characters can be used.

Any leading or trailing whitespace will be stripped. The layout will be
parsed for correctness and an exception will be raised if any errors are
detected.

Tournament Setup
----------------

If you are participating in the `Python Summer School, St Andrews, Scotland,
2011 <https://python.g-node.org/wiki/>`_, use the following instructions to
organize your files such that we can load your players during the
tournament.  You will need to create a python package, i.e. a
directory containing (at least) an ``__init__.py`` file. This package
must be named ``groupN``, where ``N`` is your group number.
This package needs to provide a top level function ``factory()`` which
returns a ``SimpleTeam``.

The file structure should look like::

    groupN
    ├── __init__.py
    ├── utils.py
    └── my_player.py

Download a :download:`template for this file structure <groupN-template.zip>`.

Your ``__init__.py`` could look like:

.. literalinclude:: groupN/__init__.py

Your are encouraged to structure your code base into packages.
Always remember to use `relative imports
<http://www.python.org/dev/peps/pep-0328/>`_. Note that relative imports only
work for modules, so you must provide a ``__init__.py`` file in that case.
For example the function ``utility`` is provided by the module ``groupN.utils``:

.. literalinclude:: groupN/utils.py

To use this module in your ``my_player.py`` module, a relative import
``from .utils import utility`` is used:

.. literalinclude:: groupN/my_player.py

Also, please perform any additional initialisation inside this
function, since it will be called once for every game.

To run a game from a module, ensure that it exports the `factory()` function,
as it was done in ``__init__.py`` above, which will return your actual team.
Also, for a module, you would not reference the Python file but only the
module itself::

    $ ~/pelita/pelitagame /home/student/groupN/ BFSPlayer,BasicDefensePlayer

or, if you would be using a differently named factory method::

    $ ~/pelita/pelitagame /home/student/groupN/:second_factory BFSPlayer,BasicDefensePlayer


Debugging
=========

The ``pelitagame`` script runs the client code in another process. Therefore,
it is not possible from the client process to halt the program and interact
with standard input. In order to use debugging methods, one has to somehow run
the player code in the main process. Depending on whether one wants to check
the left or the right, one has to use the flags `--standalone-left` and
`--standalone-right`, respectively.

For a start, let us consider a Player which does nothing but call the Python
debugger for help:

.. literalinclude:: ../../pelita/player.py
   :prepend: import pdb
   :pyobject: DebuggablePlayer

We want to use this player in our left team and let the server choose a random
team for the right hand side. Additionally, we disable the timeouts::

    $ ~/pelita/pelitagame --standalone-left --no-timeout DebuggablePlayer

We now can interact with the game by manually setting the direction at
each step::

    > ./pelita/player.py(494)get_move()
    -> return direction
    (Pdb) direction = (1,0)
    (Pdb) c
    > ./pelita/player.py(494)get_move()
    -> return direction
    (Pdb) direction = (0,1)
    (Pdb) c
    > ./pelita/player.py(494)get_move()
    -> return direction
    (Pdb)

.. note::

    The standalone mode may sometimes misbehave. Possible issues may include
    the occasional not responding on keystrokes, garbled output and the
    failure to automatically shutdown the program. In these cases, it is
    useful to press the keyboard interrupt (CTRL+C) a couple of times.

