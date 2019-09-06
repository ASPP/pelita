# This bot shows how to enable a debugger session to explore the objects
# IMPORTANT: timeouts need to be disabled, or you will not have time to use
# the debugger at all. Run a game with:
# pelita --no-timeout demo08_debugger.py demo01_stopping.py
# The debugger works automatically also inside of pytest

TEAM_NAME = 'Debuggable Bot'

def move(bot, state):
    breakpoint()
    return (0,0)
