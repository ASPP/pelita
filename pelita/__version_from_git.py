# -*- coding: utf-8 -*-

import os
import subprocess

__docformat__ = "restructuredtext"


def __get_command_output(command_string, cwd=None):
    """ Execute arbitrary commands.

    Parameters
    ----------
    command_list : strings
        the command and its arguments

    cwd : string
        the directory where the command should be executed

    Returns
    -------
    output : string
        the raw output of the command executed
    """

    command_list = command_string.split(' ')
    p = subprocess.Popen(command_list, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, cwd=cwd)
    p.wait()
    return p.returncode, p.stdout.read(), p.stderr.read()

class __GitException(Exception):
    pass

def __get_git_output(command, directory):
    try:
        ret_code, output, error = __get_command_output('git %s' % command,
            cwd=directory)
    except OSError as e:
        # if git is not installed, an OSError is raised
        raise __GitException(e)
    if ret_code != 0:
        raise __GitException(error)
    else:
        return output.strip()

def __is_git_repo(directory):
    try:
        __get_git_output('rev-parse', directory)
    except __GitException:
        return False
    else:
        return True

def __git_describe(directory):
    return __get_git_output('describe', directory)

def version():
    pelita_dir = os.path.dirname(__file__)
    if __is_git_repo(pelita_dir):
        return __git_describe(pelita_dir)
