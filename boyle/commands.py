# coding=utf-8
#------------------------------------------------------------------------------

#Author: Alexandre Manhaes Savio
#Grupo de Inteligencia Computational <www.ehu.es/ccwintco>
#Universidad del Pais Vasco UPV/EHU

#License: 3-Clause BSD

#2013, Alexandre Manhaes Savio
#Use this at your own risk!
#------------------------------------------------------------------------------

import os
import os.path as op
import sys
import shutil
import inspect
import subprocess
import logging
from   subprocess import CalledProcessError


log = logging.getLogger(__name__)


def which(program):
    """Returns the absolute path of the given CLI program name."""
    if (sys.version_info > (3, 0)):
        return which_py3(program)
    else:
       # Python 2 code in this block
        return which_py2(program)


def which_py3(program):
    return shutil.which(program)


def which_py2(program):
    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

    return None


def whoami():
    """Get the name of the current function"""
    return inspect.stack()[1][3]


def whosdaddy():
    """Get the name of the current function"""
    return inspect.stack()[2][3]


def die(msg, code=-1):
    """Writes msg to stderr and exits with return code"""
    sys.stderr.write(msg + "\n")
    sys.exit(code)


def check_call(cmd_args):
    """
    Calls the command

    Parameters
    ----------
    cmd_args: list of str
        Command name to call and its arguments in a list.

    Returns
    -------
    Command output
    """
    p = subprocess.Popen(cmd_args, stdout=subprocess.PIPE)
    (output, err) = p.communicate()
    return output


def call_command(cmd_name, args_strings):
    """Call CLI command with arguments and returns its return value.

    Parameters
    ----------
    cmd_name: str
        Command name or full path to the binary file.

    arg_strings: list of str
        Argument strings list.

    Returns
    -------
    return_value
        Command return value.
    """
    if not op.isabs(cmd_name):
        cmd_fullpath = which(cmd_name)
    else:
        cmd_fullpath = cmd_name

    try:
        cmd_line = [cmd_fullpath] + args_strings

        log.info('Calling: {}.'.format(cmd_line))
        retval = subprocess.check_call(cmd_line)
    except CalledProcessError as ce:
        log.exception("Error calling command {} with arguments: "
                      "{} \n With return code: {}".format(cmd_name, args_strings,
                                                          ce.returncode))
        raise
    else:
        return retval


def condor_call(cmd, shell=True):
    """
    Tries to submit cmd to HTCondor, if it does not succeed, it will
    be called with subprocess.call.

    Parameters
    ----------
    cmd: string
        Command to be submitted

    Returns
    -------
    """
    log.info(cmd)
    ret = condor_submit(cmd)
    if ret != 0:
        subprocess.call(cmd, shell=shell)


def condor_submit(cmd):
    """
    Submits cmd to HTCondor queue

    Parameters
    ----------
    cmd: string
        Command to be submitted

    Returns
    -------
    int
        returncode value from calling the submission command.
    """
    is_running = subprocess.call('condor_status', shell=True) == 0
    if not is_running:
        raise CalledProcessError('HTCondor is not running.')

    sub_cmd = 'condor_qsub -shell n -b y -r y -N ' \
              + cmd.split()[0] + ' -m n'

    log.info('Calling: ' + sub_cmd)

    return subprocess.call(sub_cmd + ' ' + cmd, shell=True)


# if [ $scriptmode -ne 1 ] ; then
#     sge_command="$qsub_cmd -V -cwd -shell n -b y -r y $queueCmd $pe_options -M $mailto -N $JobName -m $MailOpts $LogOpts $sge_arch $sge_hol
# d"
# else
#     sge_command="$qsub_cmd $LogOpts $sge_arch $sge_hold"
# fi
# if [ $verbose -eq 1 ] ; then
#     echo sge_command: $sge_command >&2
#     echo executing: $@ >&2
# fi
# exec $sge_command $@ | awk '{print $3}'
