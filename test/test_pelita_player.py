import py_compile
import sys
import tempfile
from pathlib import Path

import pytest

from pelita.scripts.pelita_player import load_team, load_team_from_module, sanitize_team_name

_mswindows = (sys.platform == "win32")

SIMPLE_MODULE = """
from pelita.player import stopping_player
TEAM_NAME = "%s"
move = stopping_player
"""

SIMPLE_FAILING_MODULE = """
def noteam():
    return None
"""

MODULE_IMPORT_ERROR = """
import .broken
TEAM_NAME = "noteam"
def move(bot, state):
    return bot.position
"""

# We do not want to clutter sys.modules too much and also avoid import errors when
# a module of the same name has been imported before.
# With cleanup_test_modules we ensure that imported names are cleared again after a test

class AutoCleanModules:
    def __init__(self, modules):
        self.modules = modules

@pytest.fixture
def cleanup_test_modules(request):

    # Use a marker like
    #     @pytest.mark.cleanup_test_modules(["test-team-a", "test-team-b"])
    # to override the module names that are to be cleaned up

    marker = request.node.get_closest_marker("cleanup_test_modules")
    if marker is None:
        modules = ['test_module']
    else:
        modules = marker.args[0]

    for module in modules:
        if module in sys.modules:
            raise RuntimeError(f"Test module {module} is already in sys.modules.")

    auto_clean_modules = AutoCleanModules(modules)

    yield auto_clean_modules

    for module in auto_clean_modules.modules:
        del sys.modules[module]


@pytest.mark.cleanup_test_modules(["teamx"])
def test_simple_module_import(cleanup_test_modules):
    with tempfile.TemporaryDirectory() as d:
        module = Path(d) / "teamx"
        module.mkdir()
        initfile = module / "__init__.py"
        with initfile.open(mode='w') as f:
            f.write(SIMPLE_MODULE)

        spec = str(module)
        load_team_from_module(spec)

@pytest.mark.cleanup_test_modules(["teamyy"])
def test_simple_file_import(cleanup_test_modules):
    with tempfile.TemporaryDirectory() as d:
        module = Path(d) / "teamy"
        module.mkdir()
        initfile = module / "teamyy.py"
        with initfile.open(mode='w') as f:
            f.write(SIMPLE_MODULE)

        spec = str(initfile)
        load_team_from_module(spec)

@pytest.mark.cleanup_test_modules(["teamz"])
def test_failing_import(cleanup_test_modules):
    with tempfile.TemporaryDirectory() as d:
        module = Path(d) / "teamz"
        module.mkdir()
        initfile = module / "__init__.py"
        with initfile.open(mode='w') as f:
            f.write(SIMPLE_FAILING_MODULE)

        spec = str(module)
        with pytest.raises(AttributeError):
            load_team_from_module(spec)

@pytest.mark.cleanup_test_modules(["teampycpyc"])
def test_import_of_pyc(cleanup_test_modules):
    with tempfile.TemporaryDirectory() as d:
        module = Path(d) / "teampyc"
        module.mkdir()
        initfile = module / "teampycpyc.py"
        with initfile.open(mode='w') as f:
            f.write(SIMPLE_MODULE)
        pycfile = initfile.parent / "teampycpyc.pyc"
        py_compile.compile(str(initfile), cfile=str(pycfile))
        initfile.unlink()

        spec = str(pycfile)
        load_team_from_module(spec)

# No cleanup needed. Module is not imported
def test_failing_import_importerror():
    assert "teamzab" not in sys.modules
    with tempfile.TemporaryDirectory() as d:
        module = Path(d) / "teamzab"
        module.mkdir()
        initfile = module / "__init__.py"
        with initfile.open(mode='w') as f:
            f.write(MODULE_IMPORT_ERROR)
        broken_module = module / "broken.py"
        with broken_module.open(mode='w') as f:
            f.write('this is a syntax error\n')

        spec = str(module)

        with pytest.raises(SyntaxError):
            load_team_from_module(spec)

    assert "teamzab" not in sys.modules


@pytest.mark.parametrize('name, expected', [
    ("a", True),
    ("a a", True),
    ("0" * 25, True),
    ("", "???"),
    (" ", "???"),
    ("-", "???"),
    ("∂", "???"),
    ("0" * 26, "0" * 25),
    (" " + "0" * 26, "0" * 25),
])
def test_player_import_name(name, expected, cleanup_test_modules):
    with tempfile.TemporaryDirectory() as d:
        # we must have a unused file name
        team_file = Path(d) / "test_module.py"
        with team_file.open(mode='w') as f:
            try:
                f.write(SIMPLE_MODULE % (name,))
            except UnicodeEncodeError:
                if _mswindows:
                    # Ignore UnicodeEncodeErrors on Windows for this test
                    # It is too complicate to debug this

                    # No module has been imported; ensure that nothing is cleaned up
                    cleanup_test_modules.modules = []
                    return
                else:
                    raise

        spec = str(team_file)
        if expected is True:
            assert load_team(spec).team_name == name
        else:
            assert load_team(spec).team_name == expected


@pytest.mark.parametrize('name, expected', [
    ("a", True),
    ("a a", True),
    ("0" * 25, True),
    ("", "???"),
    (" ", "???"),
    ("-", "???"),
    ("∂", "???"),
    ("0" * 26, "0" * 25),
    (" " + "0" * 26, "0" * 25),
])
def test_sanitize_team_name(name, expected):
    if expected is True:
        assert sanitize_team_name(name) == name
    else:
        assert sanitize_team_name(name) == expected


@pytest.mark.parametrize('team_spec, expected', [
    ("pelita/player/StoppingPlayer", None),
    ("NonExistingPlayer", ImportError),
    #('doc/source/groupN', AttributeError), # TODO: Should be rewritten for a proper team
    #('doc/source/groupN/__init__.py', ImportError), # TODO: Should be rewritten for a proper team
])
def test_load_team(team_spec, expected):

    if expected is not None:
        with pytest.raises(expected):
            load_team(team_spec)
    else:
        load_team(team_spec)
