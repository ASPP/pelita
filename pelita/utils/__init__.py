# -*- coding: utf-8 -*-

import sys
import contextlib as _contextlib
from .threading_helpers import *
from .debug import *

__docformat__ = "restructuredtext"

@_contextlib.contextmanager
def with_sys_path(dirname):
    sys.path.insert(0, dirname)
    try:
        yield
    finally:
        sys.path.remove(dirname)
