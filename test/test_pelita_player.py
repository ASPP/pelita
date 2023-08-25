import pytest

from pathlib import Path
import py_compile
import sys
import tempfile

import pelita
from pelita.scripts.pelita_player import load_team_from_module, load_team

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

# TODO: The modules should be unloaded after use
# If we import modules with the same name again, the results will be very unexpected

class TestLoadFactory:
    def test_simple_module_import(self):
        modules_before = list(sys.modules.keys())
        with tempfile.TemporaryDirectory() as d:
            module = Path(d) / "teamx"
            module.mkdir()
            initfile = module / "__init__.py"
            with initfile.open(mode='w') as f:
                f.write(SIMPLE_MODULE)

            spec = str(module)
            load_team_from_module(spec)

    def test_simple_file_import(self):
        modules_before = list(sys.modules.keys())
        with tempfile.TemporaryDirectory() as d:
            module = Path(d) / "teamy"
            module.mkdir()
            initfile = module / "teamyy.py"
            with initfile.open(mode='w') as f:
                f.write(SIMPLE_MODULE)

            spec = str(initfile)
            load_team_from_module(spec)

    def test_failing_import(self):
        modules_before = list(sys.modules.keys())
        with tempfile.TemporaryDirectory() as d:
            module = Path(d) / "teamz"
            module.mkdir()
            initfile = module / "__init__.py"
            with initfile.open(mode='w') as f:
                f.write(SIMPLE_FAILING_MODULE)

            spec = str(module)
            with pytest.raises(AttributeError):
                load_team_from_module(spec)

    def test_import_of_pyc(self):
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

    def test_failing_import_importerror(self):
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

class TestLoadTeam:
    def test_simple_module_import_forbidden_names(self):
        names = ["", " ", "-", "∂", "0" * 26]
        for idx, name in enumerate(names):
            modules_before = list(sys.modules.keys())
            with tempfile.TemporaryDirectory() as d:
                module = Path(d) / ("teamx_%i" % idx)
                module.mkdir()
                initfile = module / "__init__.py"
                with initfile.open(mode='w') as f:
                    try:
                        f.write(SIMPLE_MODULE % (name,))
                    except UnicodeEncodeError:
                        if _mswindows:
                            # Ignore UnicodeEncodeErrors on Windows for this test
                            # It is too complicate to debug this
                            continue
                        else:
                            raise

                spec = str(module)
                with pytest.raises(ValueError):
                    load_team(spec)

    def test_simple_module_import_allowed_names(self):
        names = ["a", "a a", "0" * 25]
        for idx, name in enumerate(names):
            modules_before = list(sys.modules.keys())
            with tempfile.TemporaryDirectory() as d:
                module = Path(d) / ("teamy_%i" % idx)
                module.mkdir()
                initfile = module / "__init__.py"
                with initfile.open(mode='w') as f:
                    f.write(SIMPLE_MODULE % (name,))

                spec = str(module)
                load_team(spec)

    # These test cases need to be handled in one function
    # ie. not in a parametrized test, as the will need
    # to be run inside the same Python session
    load_team_cases = [
        ("pelita/player/StoppingPlayer", None),
#        ("StoppingPlayer,StoppingPlayer", None),
        ("NonExistingPlayer", ImportError),
#        ("StoppingPlayer,StoppingPlayer,FoodEatingPlayer", ValueError),
        #('doc/source/groupN', AttributeError), # TODO: Should be rewritten for a proper team
        #('doc/source/groupN/__init__.py', ImportError), # TODO: Should be rewritten for a proper team
        #('doc/source/groupN', ValueError), # Has already been imported
    ]

    def test_load_team(self):
        for path, result in self.load_team_cases:
            print(path, result)
            if result is not None:
                with pytest.raises(result):
                    load_team(path)
            else:
                load_team(path)

