# coding=utf-8
# -------------------------------------------------------------------------------

# Author: Alexandre Manhaes Savio <alexsavio@gmail.com>
# Grupo de Inteligencia Computational <www.ehu.es/ccwintco>
# Universidad del Pais Vasco UPV/EHU
#
# 2013, Alexandre Manhaes Savio
# Use this at your own risk!
# -------------------------------------------------------------------------------

import re


def filter_objlist(olist, fieldname, fieldval):
    """
    Returns a list with of the objects in olist that have a fieldname valued as fieldval

    Parameters
    ----------
    olist: list of objects

    fieldname: string

    fieldval: anything

    Returns
    -------
    list of objets
    """
    return [x for x in olist if getattr(x, fieldname) == fieldval]


def filter_list(lst, filt):
    """
    Parameters
    ----------
    lst: list

    filter: function
        Unary string filter function

    Returns
    -------
    list
        List of items that passed the filter

    Example
    -------
    >>> l    = ['12123123', 'N123213']
    >>> filt = re.compile('\d*').match
    >>> nu_l = list_filter(l, filt)
    """
    return [m for s in lst for m in (filt(s),) if m]


def match_list(lst, pattern, group_names=[]):
    """
    Parameters
    ----------
    lst: list of str

    regex: string

    group_names: list of strings
        See re.MatchObject group docstring

    Returns
    -------
    list of strings
        Filtered list, with the strings that match the pattern
    """
    filtfn = re.compile(pattern).match
    filtlst = filter_list(lst, filtfn)
    if not group_names:
        return [m.string for m in filtlst]
    else:
        return [m.group(group_names) for m in filtlst]


def search_list(lst, pattern):
    """

    Parameters
    ----------
    pattern: string

    lst: list of strings

    Returns
    -------
    filtered_list: list of str
        Filtered lists with the strings in which the pattern is found.
    """
    filt = re.compile(pattern).search
    return filter_list(lst, filt)


def append_to_keys(adict, preffix):
    """
    Parameters
    ----------
    adict:
    preffix:

    Returns
    -------

    """
    return {preffix + str(key): (value if isinstance(value, dict) else value)
            for key, value in list(adict.items())}


def append_to_list(lst, preffix):
    """
    Parameters
    ----------
    lst:
    preffix:

    Returns
    -------
    """
    return [preffix + str(item) for item in lst]


def is_valid_regex(string):
    """
    Checks whether the re module can compile the given regular expression.

    Parameters
    ----------
    string: str

    Returns
    -------
    boolean
    """
    try:
        re.compile(string)
        is_valid = True
    except re.error:
        is_valid = False
    return is_valid


def is_regex(string):
    """
    TODO: improve this!

    Returns True if the given string is considered a regular expression,
    False otherwise.
    It will be considered a regex if starts with a non alphabetic character
    and then correctly compiled by re.compile

    :param string: str

    """
    is_regex = False
    regex_chars = ['\\', '(', '+', '^', '$']
    for c in regex_chars:
        if string.find(c) > -1:
            return is_valid_regex(string)
    return is_regex


def is_fnmatch_regex(string):
    """
    Returns True if the given string is considered a fnmatch
    regular expression, False otherwise.
    It will look for

    :param string: str

    """
    is_regex = False
    regex_chars = ['!', '*', '$']
    for c in regex_chars:
        if string.find(c) > -1:
            return True
    return is_regex


def remove_from_string(string, values):
    """

    Parameters
    ----------
    string:
    values:

    Returns
    -------
    """
    for v in values:
        string = string.replace(v, '')

    return string


def count_hits(strings, pattern):
    count = 0
    for s in strings:
        if re.match(pattern, s):
            count += 1
    return count


def where_is(strings, pattern, n=1, lookup_func=re.match):
    """Return index of the nth match found of pattern in strings

    Parameters
    ----------
    strings: list of str
        List of strings

    pattern: str
        Pattern to be matched

    nth: int
        Number of times the match must happen to return the item index.

    lookup_func: callable
        Function to match each item in strings to the pattern, e.g., re.match or re.search.

    Returns
    -------
    index: int
        Index of the nth item that matches the pattern.
        If there are no n matches will return -1
    """
    count = 0
    for idx, item in enumerate(strings):
        if lookup_func(pattern, item):
            count += 1
            if count == n:
                return idx
    return -1


def to_str(bytes_or_str):
    if isinstance(bytes_or_str, bytes):
        value = bytes_or_str.decode('utf-8')
    else:
        value = bytes_or_str
    return value  # Instance of str”


def to_bytes(bytes_or_str):
    if isinstance(bytes_or_str, str):
        value = bytes_or_str.encode('utf-8')
    else:
        value = bytes_or_str
    return value # Instance of bytes”


# Python 2
def to_unicode(unicode_or_str):
    if isinstance(unicode_or_str, str):
        value = unicode_or_str.decode('utf-8')
    else:
        value = unicode_or_str
    return value # Instance of unicode


# Python 2
def to_str2(unicode_or_str):
    if isinstance(unicode_or_str, unicode):
        value = unicode_or_str.encode('utf-8')
    else:
        value = unicode_or_str
    return value # Instance of str”
