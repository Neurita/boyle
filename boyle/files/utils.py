# coding=utf-8
"""
Utilities for file management.
"""
# ------------------------------------------------------------------------------
# Author: Alexandre Manhaes Savio <alexsavio@gmail.com>
#
# 2015, Alexandre Manhaes Savio
# Use this at your own risk!
# ------------------------------------------------------------------------------

import os.path as op
import shutil

from .names import remove_ext, get_extension


def copy_w_ext(srcfile, destdir, basename):
    """ Copy `srcfile` in `destdir` with name `basename + get_extension(srcfile)`.
    Add pluses to the destination path basename if a file with the same name already
    exists in `destdir`.

    Parameters
    ----------
    srcfile: str

    destdir: str

    basename:str

    Returns
    -------
    dstpath: str
    """

    ext = get_extension(op.basename(srcfile))

    dstpath = op.join(destdir, basename + ext)

    return copy_w_plus(srcfile, dstpath)


def copy_w_plus(src, dst):
    """Copy file from `src` path to `dst` path. If `dst` already exists, will add '+' characters
    to the end of the basename without extension.

    Parameters
    ----------
    src: str

    dst: str

    Returns
    -------
    dstpath: str
    """
    dst_ext = get_extension(dst)
    dst_pre = remove_ext   (dst)

    while op.exists(dst_pre + dst_ext):
        dst_pre += '+'

    shutil.copy(src, dst_pre + dst_ext)

    return dst_pre + dst_ext
