# -*- coding: utf-8 -*-

from . import (compat,
               containers,
               datamodel,
               game_master,
               layout,
               player,
               #simplesetup,
               zmqsetup,
               viewer,
               __version_from_git)

__docformat__ = "restructuredtext"

version = __version_from_git.version()
