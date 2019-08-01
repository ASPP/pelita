#!/usr/bin/env python

from setuptools import setup

from pathlib import Path
import re

def find_version(path):
    version_file = Path(path).read_text()
    version_match = re.search(r'''^__version__ = ['"]([^'"]*)['"]''', version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


setup(
    version=find_version("pelita/__init__.py")
)
