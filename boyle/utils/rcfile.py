#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function

import os
import os.path as op
import socket

import configparser
from   configparser import ExtendedInterpolation


def merge(dict_1, dict_2):
    """Merge two dictionaries.

    Values that evaluate to true take priority over falsy values.
    `dict_1` takes priority over `dict_2`.

    """
    return dict((str(key), dict_1.get(key) or dict_2.get(key))
                for key in set(dict_2) | set(dict_1))


def get_environment(appname):
    prefix = '%s_' % appname.upper()
    vars = ([(k, v) for k, v in os.environ.items() if k.startswith(prefix)])

    return dict([(k.replace(prefix, '').lower(), v) for k, v in vars])


def get_config_filepaths(appname, config_file=None,
                         additional_search_path=None):
    home = op.expanduser('~')
    files = [
        op.join('/etc', appname, 'config'),
        op.join('/etc', '%src' % appname),
        op.join(home, '.config', appname, 'config'),
        op.join(home, '.config', appname),
        op.join(home, '.%s' % appname, 'config'),
        op.join(home, '.%src' % appname),
        '%src' % appname,
        '.%src' % appname,
        config_file or '',
    ]

    if additional_search_path is not None:
        files.extend([op.join(additional_search_path,  '%src' % appname),
                      op.join(additional_search_path, '.%src' % appname),
                      ])

    return files


def get_config(appname, section, config_file=None,
               additional_search_path=None):

    config = configparser.ConfigParser(interpolation=ExtendedInterpolation())
    files  = get_config_filepaths(appname, config_file, additional_search_path)
    _ = config.read(files)

    cfg_items = {}
    if config.has_section(section):
        cfg_items = dict(config.items(section))

    hn = socket.gethostname()
    host_section = '{}:{}'.format(section, hn)
    if config.has_section(host_section):
        host_items = dict (config.items(host_section))
        cfg_items  = merge(host_items, cfg_items)

    return cfg_items


def get_sections(appname, config_file=None, additional_search_path=None):
    config = configparser.ConfigParser(interpolation=ExtendedInterpolation())
    files  = get_config_filepaths(appname, config_file, additional_search_path)
    _ = config.read(files)

    return config.sections()


def get_sys_path(rcpath, app_name, section_name=None):
    """Return a folder path if it exists.

    First will check if it is an existing system path, if it is, will return it
    expanded and absoluted.

    If this fails will look for the rcpath variable in the app_name rcfiles or
    exclusively within the given section_name, if given.

    Parameters
    ----------
    rcpath: str
        Existing folder path or variable name in app_name rcfile with an
        existing one.

    section_name: str
        Name of a section in the app_name rcfile to look exclusively there for
        variable names.

    app_name: str
        Name of the application to look for rcfile configuration files.

    Returns
    -------
    sys_path: str
        A expanded absolute file or folder path if the path exists.

    Raises
    ------
    IOError if the proposed sys_path does not exist.
    """
    # first check if it is an existing path
    if op.exists(rcpath):
        return op.realpath(op.expanduser(rcpath))

    # look for the rcfile
    try:
        settings = rcfile(app_name, section_name)
    except:
        raise

    # look for the variable within the rcfile configutarions
    try:
        sys_path = op.expanduser(settings[rcpath])
    except KeyError:
        raise IOError('Could not find an existing variable with name {0} in'
                      ' section {1} of {2}rc config setup. Maybe it is a '
                      ' folder that could not be found.'.format(rcpath,
                                                                section_name,
                                                                app_name))
    # found the variable, now check if it is an existing path
    else:
        if not op.exists(sys_path):
            raise IOError('Could not find the path {3} indicated by the '
                          'variable {0} in section {1} of {2}rc config '
                          'setup.'.format(rcpath, section_name, app_name,
                                          sys_path))

        # expand the path and return
        return op.realpath(op.expanduser(sys_path))


def rcfile(appname, section=None, args={}, strip_dashes=True):
    """Read environment variables and config files and return them merged with
    predefined list of arguments.

    Parameters
    ----------
    appname: str
        Application name, used for config files and environment variable
        names.

    section: str
        Name of the section to be read. If this is not set: appname.

    args:
        arguments from command line (optparse, docopt, etc).

    strip_dashes: bool
        Strip dashes prefixing key names from args dict.

    Returns
    --------
    dict
        containing the merged variables of environment variables, config
        files and args.

    Raises
    ------
    IOError
        In case the return value is empty.

    Notes
    -----
    Environment variables are read if they start with appname in uppercase
    with underscore, for example:

        TEST_VAR=1

    Config files compatible with ConfigParser are read and the section name
    appname is read, example:

        [appname]
        var=1

    We can also have host-dependent configuration values, which have
    priority over the default appname values.

        [appname]
        var=1

        [appname:mylinux]
        var=3


    For boolean flags do not try to use: 'True' or 'False',
                                         'on' or 'off',
                                         '1' or '0'.
    Unless you are willing to parse this values by yourself.
    We recommend commenting the variables out with '#' if you want to set a
    flag to False and check if it is in the rcfile cfg dict, i.e.:

        flag_value = 'flag_variable' in cfg


    Files are read from: /etc/appname/config,
                         /etc/appfilerc,
                         ~/.config/appname/config,
                         ~/.config/appname,
                         ~/.appname/config,
                         ~/.appnamerc,
                         appnamerc,
                         .appnamerc,
                         appnamerc file found in 'path' folder variable in args,
                         .appnamerc file found in 'path' folder variable in args,
                         file provided by 'config' variable in args.

    Example
    -------
        args = rcfile(__name__, docopt(__doc__, version=__version__))
    """
    if strip_dashes:
        for k in args.keys():
            args[k.lstrip('-')] = args.pop(k)

    environ = get_environment(appname)

    if section is None:
        section = appname

    config = get_config(appname,
                        section,
                        args.get('config', ''),
                        args.get('path', ''))
    config = merge(merge(args, config), environ)

    if not config:
        raise IOError('Could not find any rcfile for application '
                      '{}.'.format(appname))

    return config

def get_rcfile_section(app_name, section_name):
    """ Return the dictionary containing the rcfile section configuration
    variables.

    Parameters
    ----------
    section_name: str
        Name of the section in the rcfiles.

    app_name: str
        Name of the application to look for its rcfiles.

    Returns
    -------
    settings: dict
        Dict with variable values
    """
    try:
        settings = rcfile(app_name, section_name)
    except IOError:
        raise
    except:
        raise KeyError('Error looking for section {} in {} '
                       ' rcfiles.'.format(section_name, app_name))
    else:
        return settings


def get_rcfile_variable_value(var_name, app_name, section_name=None):
    """ Return the value of the variable in the section_name section of the
    app_name rc file.

    Parameters
    ----------
    var_name: str
        Name of the variable to be searched for.

    section_name: str
        Name of the section in the rcfiles.

    app_name: str
        Name of the application to look for its rcfiles.

    Returns
    -------
    var_value: str
        The value of the variable with given var_name.
    """
    cfg = get_rcfile_section(app_name, section_name)

    if var_name in cfg:
        raise KeyError('Option {} not found in {} '
                       'section.'.format(var_name, section_name))

    return cfg[var_name]


def find_in_sections(var_name, app_name):
    """ Return the section and the value of the variable where the first
    var_name is found in the app_name rcfiles.

    Parameters
    ----------
    var_name: str
        Name of the variable to be searched for.

    app_name: str
        Name of the application to look for its rcfiles.

    Returns
    -------
    section_name: str
        Name of the section in the rcfiles where var_name was first found.

    var_value: str
        The value of the first variable with given var_name.
    """
    sections = get_sections(app_name)

    if not sections:
        raise ValueError('No sections found in {} rcfiles.'.format(app_name))

    for s in sections:
        try:
            var_value = get_rcfile_variable_value(var_name, section_name=s,
                                                  app_name=app_name)
        except:
            pass
        else:
            return s, var_value

    raise KeyError('No variable {} has been found in {} '
                   'rcfiles.'.format(var_name, app_name))
