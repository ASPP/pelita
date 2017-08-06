
import contextlib as _contextlib
import logging
import sys

@_contextlib.contextmanager
def with_sys_path(dirname):
    sys.path.insert(0, dirname)
    try:
        yield
    finally:
        sys.path.remove(dirname)


def start_logging(filename):
    if filename:
        hdlr = logging.FileHandler(filename, mode='w')
    else:
        hdlr = logging.StreamHandler()
    logger = logging.getLogger('pelita')
    FORMAT = '[%(relativeCreated)06d %(name)s:%(levelname).1s][%(funcName)s] %(message)s'
    formatter = logging.Formatter(FORMAT)
    hdlr.setFormatter(formatter)
    logger.addHandler(hdlr)
    logger.setLevel(logging.DEBUG)
