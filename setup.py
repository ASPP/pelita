"""A setuptools based setup module.

See:
https://packaging.python.org/en/latest/distributing.html
https://github.com/pypa/sampleproject
"""

import io
import os
import re
import sys

# Always prefer setuptools over distutils
from setuptools import setup, find_packages
from setuptools.command.test import test as _test
# To use a consistent encoding
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))


def read(*names, **kwargs):
    with io.open(
        os.path.join(os.path.dirname(__file__), *names),
        encoding=kwargs.get("encoding", "utf8")
    ) as fp:
        return fp.read()

def find_version(*file_paths):
    version_file = read(*file_paths)
    version_match = re.search(r'''^__version__ = ['"]([^'"]*)['"]''', version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


class PelitaPyTest(_test):
    user_options = [('pytest-args=', 'a', "Arguments to pass to pytest")]

    def initialize_options(self):
        _test.initialize_options(self)
        self.pytest_args = []

    def run_tests(self):
        import shlex
        #import here, cause outside the eggs aren't loaded
        import pytest
        if self.pytest_args:
            args = shlex.split(self.pytest_args)
        else:
            args = None
        errno = pytest.main(args)
        sys.exit(errno)


# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='pelita',

    # Versions should comply with PEP440.  For a discussion on single-sourcing
    # the version across setup.py and the project code, see
    # https://packaging.python.org/en/latest/single_source_version.html
    version=find_version("pelita", "__init__.py"),

    description='Pelita',
    long_description=long_description,

    # The project's main homepage.
    url='https://github.com/ASPP/pelita',

    # Author details
    #author='The Python Packaging Authority',
    #author_email='pypa-dev@googlegroups.com',

    # Choose your license
    license='BSD-2',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 4 - Beta',

        # Indicate who your project is intended for
        'Intended Audience :: Education',
        'Topic :: Scientific/Engineering :: Artificial Intelligence',

        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: BSD License',

        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],

    # What does your project relate to?
    keywords='education',

    # You can just specify the packages manually here if your project is
    # simple. Or you can use find_packages().
    packages=['pelita', 'pelita.scripts', 'pelita.ui', 'pelita.utils', 'pelita.players', 'pelita.tournament'],


    # Alternatively, if you want to distribute just a my_module.py, uncomment
    # this:
    #   py_modules=["my_module"],

    # List run-time dependencies here.  These will be installed by pip when
    # your project is installed. For an analysis of "install_requires" vs pip's
    # requirements files see:
    # https://packaging.python.org/en/latest/requirements.html
    install_requires=['pyzmq'],

    tests_require = ['pytest'],

    # List additional groups of dependencies here (e.g. development
    # dependencies). You can install these using the following syntax,
    # for example:
    # $ pip install -e .[dev,test]
    extras_require={
        'tournament': ["PyYAML", "numpy"]
    },

    # If there are data files included in your packages that need to be
    # installed, specify them here.  If using Python 2.6 or less, then these
    # have to be included in MANIFEST.in as well.
    package_data={
    },

    # Although 'package_data' is the preferred approach, in some case you may
    # need to place data files outside of your packages. See:
    # http://docs.python.org/3.4/distutils/setupscript.html#installing-additional-files # noqa
    # In this case, 'data_file' will be installed into '<sys.prefix>/my_data'
    #data_files=[('my_data', ['data/data_file'])],

    # To provide executable pelita.scripts, use entry points in preference to the
    # "pelita.scripts" keyword. Entry points provide cross-platform support and allow
    # pip to create the appropriate form of executable for the target platform.
    entry_points={
        'console_scripts': [
            'pelita=pelita.scripts.pelita_main:main',
            'pelita-tournament=pelita.scripts.pelita_tournament:main [tournament]',
            'pelita-tkviewer=pelita.scripts.pelita_tkviewer:main',
            'pelita-player=pelita.scripts.pelita_player:main',
        ],
    },

    cmdclass={
        'test': PelitaPyTest
    }
)