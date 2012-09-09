#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" Runs a viewer which tries to connect with a remote server
on the standard port.
"""

from pelita.simplesetup import SimpleViewer

viewer = SimpleViewer(local=False)
viewer.run_tk()
