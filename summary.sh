#!/bin/zsh

wc -l **/*.py

wc -l test/**/*.py

pylint pelita

pylint test/**.py

pep8 pelita

grep 'assert' -c test/test_universe.py

nosetests --with-coverage

