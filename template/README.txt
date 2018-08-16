# Pelita demo player package

## Notes on writing

* Please use Python 3
* Numpy is pre-installed on the tournament machine; everything else must be negotiated
* Please use relative imports inside your package
* All `pelita` commands should be run from the root of the repository (or outside of it), never from inside the `team/` folder, for example
* Simple testing can be done with help of the `Makefile`

## Files

### `team/`

The main package which contains all your team’s code. Please use relative imports from inside the package.

### `team/__init__.py`

The packages’s `__init__.py` is required to contain a function `team` which is supposed to return the main players for the tournament, for example:

    def team():
        return SimpleTeam("Local marsupial team", KangarooPlayer(), KoalaPlayer())

### `team/demo_player.py`

Contains the code for a simple demo player. This player can then be imported in the `__init__.py` file.

### `team/utils.py`

This could be a good place for global utility functions (but feel free to add more files for this, if needed)

### `test/test_demo_player.py`

Simple unittest for your player. Note the relative imports. You can run tests using py.test, which automatically executes all tests in the `test/` directory.

    $ PYTHONPATH=. pytest test/
    .
    ----------------------------------------------------------------------
    Ran 1 test in 0.025s

    OK


## Makefile

We have a `Makefile` for a few quick tasks.

Per default, running `make` will start a game against a random player, and randomly choosing the side, the team is playing at. Running an explicit `make left` or `make right` will specify the position. (For more control, it is of course advised to use the `pelita` command directly.

`make test` will run `pytest` on the `test/` directory, so be sure to run it once in a while. And also add your own tests to the test folder.
