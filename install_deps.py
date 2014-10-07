#!/usr/bin/env python

"""
Install the packages you have listed in the requirements file you input as
first argument.
"""

from __future__ import (absolute_import, division, print_function, 
                        unicode_literals)

import sys
import fileinput
import subprocess
from pip.req import parse_requirements


def get_requirements(*args):
    """Parse all requirements files given and return a list of the 
       dependencies"""
    install_deps = []
    try:
        for fpath in args:
            install_deps.extend([str(d.req) for d in parse_requirements(fpath)])
    except:
        print('Error reading {} file looking for dependencies.'.format(fpath))

    return install_deps


if __name__ == '__main__':

    for line in fileinput.input():
        req_filepaths = sys.argv[1:]

    deps = get_requirements(*req_filepaths)

    try:
        for dep_name in deps:
            if dep_name == 'None':
                continue

            cmd = "pip install {0}".format(dep_name)
            print('#', cmd)
            subprocess.check_call(cmd, shell=True)
    except:
        print('Error installing {}'.format(dep_name))
