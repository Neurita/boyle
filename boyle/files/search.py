# coding=utf-8
"""
Function helpers to search for files using glob, re and os.walk.
"""
#-------------------------------------------------------------------------------

#Author: Alexandre Manhaes Savio <alexsavio@gmail.com>
#Grupo de Inteligencia Computational <www.ehu.es/ccwintco>
#Universidad del Pais Vasco UPV/EHU
#
#2013, Alexandre Manhaes Savio
#Use this at your own risk!
#-------------------------------------------------------------------------------

import re
import os
import shutil
import os.path as op
from glob import glob
from ..utils.strings import search_list, filter_list


def check_file_exists(filepath):
    """Check if the file path exists, if not raise IOError"""
    if not op.exists(filepath):
        raise IOError('File {} not found.'.format(filepath))


def dir_search(regex, wd=os.curdir):
    """
    @param regex: string
    @param wd: string
     working directory
    @return:
    """
    ls = os.listdir(wd)

    filt = re.compile(regex).search
    return filter_list(ls, filt)


def dir_match(regex, wd=os.curdir):
    """Create a list of regex matches that result from the match_regex
    of all file names within wd.
    The list of files will have wd as path prefix.

    @param regex: string
    @param wd: string
    working directory
    @return:
    """
    ls = os.listdir(wd)

    filt = re.compile(regex).match
    return filter_list(ls, filt)


def recursive_dir_match(folder_path, regex=''):
    """
    Returns absolute paths of folders that match the regex within folder_path and
    all its children folders.

    Note: The regex matching is done using the match function
    of the re module.

    Parameters
    ----------
    folder_path: string

    regex: string

    Returns
    -------
    A list of strings.
    """
    outlist = []
    for root, dirs, files in os.walk(folder_path):
        outlist.extend([op.join(root, f) for f in dirs
                        if re.match(regex, f)])

    return outlist


def get_file_list(file_dir, regex=''):
    """
    Creates a list of files that match the search_regex within file_dir.
    The list of files will have file_dir as path prefix.

    Parameters
    ----------
    @param file_dir:

    @param search_regex:

    Returns:
    --------
    List of paths to files that match the search_regex
    """
    file_list = os.listdir(file_dir)
    file_list.sort()

    if regex:
        file_list = search_list(file_list, regex)

    file_list = [op.join(file_dir, fname) for fname in file_list]

    return file_list


def recursive_find(folder_path, regex=''):
    """
    Returns absolute paths of files that match the regex within file_dir and
    all its children folders.

    Note: The regex matching is done using the search function
    of the re module.

    Parameters
    ----------
    folder_path: string

    regex: string

    Returns
    -------
    A list of strings.

    """
    return recursive_find_search(folder_path, regex)


def recursive_find_match(folder_path, regex=''):
    """
    Returns absolute paths of files that match the regex within folder_path and
    all its children folders.

    Note: The regex matching is done using the match function
    of the re module.

    Parameters
    ----------
    folder_path: string

    regex: string

    Returns
    -------
    A list of strings.

    """
    outlist = []
    for root, dirs, files in os.walk(folder_path):
        outlist.extend([op.join(root, f) for f in files
                        if re.match(regex, f)])

    return outlist


def recursive_find_search(folder_path, regex=''):
    """
    Returns absolute paths of files that match the regex within file_dir and
    all its children folders.

    Note: The regex matching is done using the search function
    of the re module.

    Parameters
    ----------
    folder_path: string

    regex: string

    Returns
    -------
    A list of strings.

    """
    outlist = []
    for root, dirs, files in os.walk(folder_path):
        outlist.extend([op.join(root, f) for f in files
                        if re.search(regex, f)])

    return outlist


def iter_recursive_find(folder_path, *regex):
    """
    Returns absolute paths of files that match the regexs within folder_path and
    all its children folders.

    This is an iterator function that will use yield to return each set of
    file_paths in one iteration.

    Will only return value if all the strings in regex match a file name.

    Note: The regex matching is done using the search function
    of the re module.

    Parameters
    ----------
    folder_path: string

    regex: strings

    Returns
    -------
    A list of strings.
    """
    for root, dirs, files in os.walk(folder_path):
        if len(files) > 0:
            outlist = []
            for f in files:
                for reg in regex:
                    if re.search(reg, f):
                        outlist.append(op.join(root, f))
            if len(outlist) == len(regex):
                yield outlist


def get_all_files(folder):
    """
    Generator that loops through all absolute paths of the files within folder

    Parameters
    ----------
    folder: str
    Root folder start point for recursive search.

    Yields
    ------
    fpath: str
    Absolute path of one file in the folders
    """
    for path, dirlist, filelist in os.walk(folder):
        for fn in filelist:
            yield op.join(path, fn)


def find_match(base_directory, regex=''):
    """
    Uses glob to find all files that match the regex
    in base_directory.

    @param base_directory: string

    @param regex: string

    @return: set
    """
    return glob(op.join(base_directory, regex))


def recursive_glob(base_directory, regex=''):
    """
    Uses glob to find all files or folders that match the regex
    starting from the base_directory.

    Parameters
    ----------
    base_directory: str

    regex: str

    Returns
    -------
    files: list

    """
    files = glob(op.join(base_directory, regex))
    for path, dirlist, filelist in os.walk(base_directory):
        for dir_name in dirlist:
            files.extend(glob(op.join(path, dir_name, regex)))

    return files


def recursive_remove(work_dir, regex='*'):
    [os.remove(fn) for fn in recursive_glob(work_dir, regex)]


def recursive_rmtrees(work_dir, regex='*'):
    [shutil.rmtree(fn, ignore_errors=True) for fn in recursive_glob(work_dir, regex)]


def get_last_file(input_dir, glob_pattern='*', key=op.getctime, reverse=True):
    """ Return the path to the latest file in `input_dir`.
     The `key` argument defines which information to use for sorting
     the list of files, could be:
        - creation date: os.path.getctime,
        - modification date: os.path.getmtime,
        etc.

    Parameters
    ----------
    input_dir: str
        Path to the folder where to perform the `glob`.

    glob_pattern: str
        `glob` Pattern to filter the files in `input_dir`.

    key: str
        Sorting key function

    reverse: bool
        Set to True if you want the sorting to be in decreasing order,
        False otherwise.

    Returns
    -------
    latest_filepath: str
        Path to the latest modified file in `input_dir`.
    """
    files = glob(op.join(input_dir, glob_pattern))
    files.sort(key=key, reverse=reverse)
    return files[0]


def get_last_modified_file(input_dir, glob_pattern='*'):
    """ Return the path to the last modified (using `os.path.getmtime`) file in `input_dir`.
    See `get_last_file` docstring for description of the parameters.
    """
    return get_last_file(input_dir, glob_pattern, key=op.getmtime)


def get_last_created_file(input_dir, glob_pattern='*'):
    """ Return the path to the last created file in `input_dir`.
    See `get_last_file` docstring for description of the parameters.
    """
    return get_last_file(input_dir, glob_pattern, key=op.getctime)
