# Pelita

## Description

Autonomous agent environment for Python summerschool.

## Git-Repository

### Layout and branch model

We use  the [gitflow](https://github.com/nvie/gitflow) model with the following settings:

  - Branch name for production releases: [master]
  - Branch name for "next release" development: [develop]
  - How to name your supporting branch prefixes?
  - Feature branches? [feature/]
  - Release branches? [release/]
  - Hotfix branches? [hotfix/]
  - Support branches? [support/]
  - Version tag prefix? [v]

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

#### Code area markers

  - DOC : documentation
  - UT  : unit tests
  - BLD : build-system setup.py
  - GIT : repository mods, e.g. .gitconfig .gitattributes

#### Example

  - DOC/ENH: add initial README.md
