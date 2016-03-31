import sys
import contextlib as _contextlib

@_contextlib.contextmanager
def with_sys_path(dirname):
    sys.path.insert(0, dirname)
    try:
        yield
    finally:
        sys.path.remove(dirname)

