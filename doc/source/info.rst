===================
Project Information
===================


Authors and Contributors
========================

As of ``v0.1.0-rc2-157-g192d87c`` the developers and contributors are::

    zsh» git shortlog -sn | cut -f1 --complement
    Valentin Haenel
    Rike-Benjamin Schuppner
    Tiziano Zito
    Zbigniew Jędrzejewski-Szmek
    Bastian Venthur
    Pietro Berkes

Getting in Touch
================

Please use our `project mailing list
<https://portal.bccn-berlin.de/cgi-bin/mailman/listinfo/pelita>`_ for questions
and discussion. Use the `GitHub issues page
<https://github.com/Debilski/pelita/issues>`_ to report bugs.

License
=======

Pelita is licensed under the terms of the `Simplified (two-clause) BSD License
<http://www.opensource.org/licenses/BSD-2-Clause>`_.
A copy of the license is included with the source, in the file ``COPYING``.

For compatibility with Python 2.6, we ship a copy of the `argparse
<http://docs.python.org/library/argparse.html>`_ module from Python 2.7. The
code is stored in ``pelita/compat/argparse.py`` and is made available as
``pelita.compat.argparse``. It's licensed under the terms of the `Python
License <http://docs.python.org/license.html>`_. Copyright and history
information for the module is included in the file ``COPYING``.

To generate API documentation from the docstring we ship a copy of the `numpydoc
<http://pypi.python.org/pypi/numpydoc>`_ sphinx extension in
``doc/sphinxext/numpydoc``. Numpydoc is licensed under various licenses, see the
file ``doc/sphinxext/numpydoc/LICENSE.txt`` for details.

Acknowledgements
================

The game is inspired by the `“Pac-Man Projects”
<http://inst.eecs.berkeley.edu/~cs188/pacman/pacman.html>`_  developed by John
DeNero and Dan Klein at Berkeley University for their artificial intelligence
introductory course [DeNeroKlein]_.

This software was developed for the “Advanced Scientific Programming in Python”
summer school, as a teaching aid for the group project.

Future:

* `St Andrews, Scotland, 2011 <https://python.g-node.org/wiki/>`_

Past:

* `Trento, Italy, 2010 <https://python.g-node.org/python-autumnschool-2010/>`_
* `Warsaw, Poland, 2010 <https://python.g-node.org/python-winterschool-2010>`_
* `Berlin, Germany, 2009 <https://python.g-node.org/python-summerschool-2009>`_

Initial funding was kindly provided by `The German Neuroinformtaics Node
<http://www.g-node.org/>`_.



References
==========

.. [DeNeroKlein] John DeNero and Dan Klein. Teaching Introductory Artificial
   Intelligence with Pac-Man. In *proceedings of the Symposium on Educational
   Advances in Artificial Intelligence (EAAI)*, 2010.
   `pdf <http://www.denero.org/content/pubs/eaai10_denero_pacman.pdf>`_
