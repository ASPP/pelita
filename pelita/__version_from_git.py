import subprocess
import sys
import os

def __get_command_output(command_string, env):
    """ Execute arbitrary commands.

    Parameters
    ----------
    command_list : strings
        the command and its arguments
    env: mapping
        mapping ov environment variables to values

    Returns
    -------
    output : string
        the raw output of the command executed
    """

    command_list = command_string.split(' ')
    p = subprocess.Popen(command_list, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, env=env)
    p.wait()
    return p.returncode, p.stdout.read(), p.stderr.read()

class __GitException(Exception):
    pass

def __get_git_output(command, directory):
    ret_code, output, error = __get_command_output('git %s' % command,
            {"GIT_WORK_TREE" : directory})
    if ret_code != 0:
        raise __GitException(error)
    else:
        return output.strip()

def __get_head_sha(directory):
    return __get_git_output('rev-parse HEAD', directory)

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
    if __is_git_repo(os.getcwd()):
        return __git_describe(os.getcwd())
