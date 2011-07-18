# Pelita

## Description

Autonomous agent environment for Python summerschool.

## Coding conventions

  - Docstrings should follow the [Numpy convention](https://github.com/numpy/numpy/blob/master/doc/HOWTO_DOCUMENT.rst.txt)
  - Use old-style `print` statement (not the function)
  - For internal messages, use the `logging` module with an appropriate logging level, which makes their appearance completely configurable.
  - Use old-style format-string, i.e. `"%s" % (val))` instead of `"{0}".format(val)`

## Git-Repository

### Layout and Branch Model

We use  the [gitflow](https://github.com/nvie/gitflow) model with the following settings:

  - Branch name for production releases: [master]
  - Branch name for "next release" development: [develop]
  - How to name your supporting branch prefixes?
  - Feature branches? [feature/]
  - Release branches? [release/]
  - Hotfix branches? [hotfix/]
  - Support branches? [support/]
  - Version tag prefix? [v]

Only *feature/* branches are subject to rebase/rewind. All others should remain
stable

### Commit Markers

Commits should be marked. Declare both functionality and area.

#### Functionality Markers

  - BF  : bug fix
  - RF  : refactoring
  - NF  : new feature
  - ENH : enhancement of an existing feature/facility
  - BW  : addresses backward-compatibility
  - OPT : optimization
  - BK  : breaks something and/or tests fail
  - FO  : code formatting (adding spaces etc.)
  - PL  : making pylint happier

#### Code Area Markers

  - DOC : documentation
  - UT  : unit tests
  - BLD : build-system, setup.py
  - GIT : repository mods, e.g. .gitconfig .gitattributes

#### Example

  - DOC/ENH: add initial README.md

## Website

We use a combination of [Sphinx](http://sphinx.pocoo.org/) and
[github-pages](http://pages.github.com/) to host the project website:
[http://debilski.github.com/pelita/](http://debilski.github.com/pelita/).

This means the sphinx generated content is keept in a seperate branch in the
source code repository `gh-pages`. This branch has its own root commit and is
hence disconnected from the commits that track the project code and also the
documentation source code.

#### To regenerate the project website:

Move to the `doc` directory:

    $ cd doc

Edit the documentation:

    $ vim source/<file>.rst

Generate html

    $ make html

Switch to the documentation branch:

    $ git checkout gh-pages

Move back up to the root directory:

    $ cd ..

Copy the generate documentation here:

    $ cp -r doc/build/html/* .

Add all tracked files that have been changed:

    $ git add -u

Add possibly new files:

    $ git add <new pages>.html

Make a commit message where `XXXXXXX` is the SHA-1
prefix of the commit the documentation was # generated from:

    $ git commit -m "sphinx generated doc from XXXXXXX"

