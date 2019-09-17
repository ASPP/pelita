"""
This module provides a single utility function. It exists mostly
to show how to share code. It is imported from demo06_one_and_one.py
and demo07_detect_death.py.
"""

def say_underlined(bot, message):
    n = len(message)
    t = message + '\n' + '-' * n
    bot.say(t)
