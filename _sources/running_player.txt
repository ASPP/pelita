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

Put the definition of you player in a file outside the Pelita source
code directory, for example in ``/home/student/my_player.py``. In addition
to the definition of your player, this file must contain a factory
function that returns a team (remember that the default game is a
fight between two teams of two bots each):

.. literalinclude:: my_player/my_player.py

The factory function is used by the command-line program to lead your
players into the game.
To run a game using your players against some predefined players in
Pelita you can run ::

       $ ~/pelita/pelitagame /home/student/my_player.py BFSPlayer,BasicDefensePlayer

This setup is OK for small tests, but if you plan to have a more
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
For example the function ``utility`` is provided my the module ``groupN.utils``:

.. literalinclude:: groupN/utils.py

To use this module in your ``my_player.py`` module, a relative import
``from .utils import utility`` is used:

.. literalinclude:: groupN/my_player.py

Also, please perform any additional initialisation inside this
function, since it will be called once for every game.

