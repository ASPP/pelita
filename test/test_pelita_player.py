import pytest

from pathlib import Path
import sys
import tempfile

import pelita
from pelita import libpelita
from pelita.scripts.pelita_player import load_factory

SIMPLE_MODULE = """
def team():
    return None
"""

SIMPLE_FAILING_MODULE = """
def noteam():
    return None
"""

def test_simple_module_import():
    modules_before = list(sys.modules.keys())
    with tempfile.TemporaryDirectory() as d:
        module = Path(d) / "teamx"
        module.mkdir()
        initfile = module / "__init__.py"
        with initfile.open(mode='w') as f:
            f.write(SIMPLE_MODULE)

        spec = str(module)
        load_factory(spec)
#        del sys.modules[module.stem]
#    assert list(sys.modules.keys()) == modules_before

def test_simple_file_import():
    modules_before = list(sys.modules.keys())
    with tempfile.TemporaryDirectory() as d:
        module = Path(d) / "teamy"
        module.mkdir()
        initfile = module / "team.py"
        with initfile.open(mode='w') as f:
            f.write(SIMPLE_MODULE)

        spec = str(initfile)
        load_factory(spec)
#        del sys.modules[module.stem]
#    assert list(sys.modules.keys()) == modules_before

def test_failing_import():
    modules_before = list(sys.modules.keys())
    with tempfile.TemporaryDirectory() as d:
        module = Path(d) / "teamz"
        module.mkdir()
        initfile = module / "__init__.py"
        with initfile.open(mode='w') as f:
            f.write(SIMPLE_FAILING_MODULE)

        spec = str(module)
        with pytest.raises(AttributeError):
            load_factory(spec)
#        del sys.modules[module.stem]
#    assert list(sys.modules.keys()) == modules_before

