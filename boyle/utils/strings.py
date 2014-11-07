# coding=utf-8
#-------------------------------------------------------------------------------

#Author: Alexandre Manhaes Savio <alexsavio@gmail.com>
#Grupo de Inteligencia Computational <www.ehu.es/ccwintco>
#Universidad del Pais Vasco UPV/EHU
#
#2013, Alexandre Manhaes Savio
#Use this at your own risk!
#-------------------------------------------------------------------------------

import re


def filter_objlist(olist, fieldname, fieldval):
    """
    Returns a list with of the objetcts in olist that have a fieldname valued as fieldval

    @param olist: list of objects
    @param fieldname: string
    @param fieldval: anything

    @return: list of objets
    """
    return [x for x in olist if getattr(x, fieldname) == fieldval]



def filter_list(lst, filt):
    """
    :param lst: list
    :param filter: function
    Unary string filter function
    :return: list
    List of strings that passed the filter

    :example
    l = ['12123123', 'N123213']
    filt = re.compile('\d*').match
    nu_l = list_filter(l, filt)
    """
    return [m for s in lst for m in (filt(s),) if m]


def match_list(lst, pattern, group_names=[]):
    """
    @param lst: list of strings

    @param regex: string

    @param group_names: list of strings
    See re.MatchObject group docstring

    @return: list of strings
    Filtered list, with the strings that match the pattern
    """
    filtfn = re.compile(pattern).match
    filtlst = filter_list(lst, filtfn)
    if group_names is None:
        return [m.string for m in filtlst]
    else:
        return [m.group(group_names) for m in filtlst]


def search_list(lst, pattern):
    """
    @param pattern: string
    @param lst: list of strings
    @return: list of strings
    Filtered lists with the strings in which the pattern is found.

    """
    filt = re.compile(pattern).search
    return filter_list(lst, filt)


def append_to_keys(adict, preffix):
    """
    @param adict:
    @param preffix:
    @return:
    """
    return {preffix + str(key): (value if isinstance(value, dict) else value)
            for key, value in list(adict.items())}


def append_to_list(lst, preffix):
    """
    @param lst:
    @param preffix:
    @return:
    """
    return [preffix + str(item) for item in lst]


def is_valid_regex(string):
    """
    Checks whether the re module can compile the given regular expression.

    :param string: str

    :return: boolean
    """
    try:
        re.compile(string)
        is_valid = True
    except re.error:
        is_valid = False
    return is_valid


def remove_from_string(string, values):
    """

    :param string:
    :param values:
    :return:
    """
    for v in values:
        string = string.replace(v, '')

    return string

