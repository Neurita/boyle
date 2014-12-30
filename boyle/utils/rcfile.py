#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function
from os.path import join, expanduser
import os
import socket
import logging

log = logging.getLogger(__name__)

try:  # Python 2
    import ConfigParser as confiparser
except ImportError:  # Python 3
    import configparser
from configparser import ExtendedInterpolation


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


def get_config_filepaths(appname, config_file=None, additional_search_path=None):
    home = expanduser('~')
    files = [
        join('/etc', appname, 'config'),
        join('/etc', '%src' % appname),
        join(home, '.config', appname, 'config'),
        join(home, '.config', appname),
        join(home, '.%s' % appname, 'config'),
        join(home, '.%src' % appname),
        '%src' % appname,
        '.%src' % appname,
        config_file or '',
    ]

    if additional_search_path is not None:
        files.extend([join(additional_search_path,  '%src' % appname),
                      join(additional_search_path, '.%src' % appname),
                      ])

    return files


def get_config(appname, section, config_file=None, additional_search_path=None):
    config = configparser.ConfigParser(interpolation=ExtendedInterpolation())
    files  = get_config_filepaths(appname, config_file, additional_search_path)
    read   = config.read(files)
    log.debug('files read: {}'.format(read))

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
    read   = config.read(files)
    log.debug('files read: {}'.format(read))

    return config.sections()


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

    config = get_config(appname, section, args.get('config', ''), args.get('path', ''))

    return merge(merge(args, config), environ)


#class HostExtendedInterpolation(ExtendedInterpolation):
#    """Advanced variant of interpolation, supports the syntax used by
#    `zc.buildout'. Enables interpolation between sections."""

#    _KEYCRE = re.compile(r"\$\{([^}]+)\}")

#    def before_get(self, parser, section, option, value, defaults):
#        L = []
#        self._interpolate_some(parser, option, L, value, section, defaults, 1)
#        return ''.join(L)

#    def before_set(self, parser, section, option, value):
#        tmp_value = value.replace('$$', '') # escaped dollar signs
#        tmp_value = self._KEYCRE.sub('', tmp_value) # valid syntax
#        if '$' in tmp_value:
#            raise ValueError("invalid interpolation syntax in %r at "
#                             "position %d" % (value, tmp_value.find('$')))
#        return value

#    def _interpolate_some(self, parser, option, accum, rest, section, map,
#                          depth):
#        if depth > MAX_INTERPOLATION_DEPTH:
#            raise InterpolationDepthError(option, section, rest)
#        while rest:
#            p = rest.find("$")
#            if p < 0:
#                accum.append(rest)
#                return
#            if p > 0:
#                accum.append(rest[:p])
#                rest = rest[p:]
#            # p is no longer used
#            c = rest[1:2]
#            if c == "$":
#                accum.append("$")
#                rest = rest[2:]
#            elif c == "{":
#                m = self._KEYCRE.match(rest)
#                if m is None:
#                    raise InterpolationSyntaxError(option, section,
#                        "bad interpolation variable reference %r" % rest)
#                path = m.group(1).split(':')
#                rest = rest[m.end():]
#                sect = section
#                opt = option
#                try:
#                    if len(path) == 1:
#                        opt = parser.optionxform(path[0])
#                        v = map[opt]
#                    elif len(path) == 2:
#                        sect = path[0]
#                        opt = parser.optionxform(path[1])
#                        v = parser.get(sect, opt, raw=True)
#                    else:
#                        raise InterpolationSyntaxError(
#                            option, section,
#                            "More than one ':' found: %r" % (rest,))
#                except (KeyError, NoSectionError, NoOptionError):
#                    raise InterpolationMissingOptionError(
#                        option, section, rest, ":".join(path))
#                if "$" in v:
#                    self._interpolate_some(parser, opt, accum, v, sect,
#                                           dict(parser.items(sect, raw=True)),
#                                           depth + 1)
#                else:
#                    accum.append(v)
#            else:
#                raise InterpolationSyntaxError(
#                    option, section,
#                    "'$' must be followed by '$' or '{', "
#                    "found: %r" % (rest,))
