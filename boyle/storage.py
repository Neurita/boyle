# coding=utf-8
#-------------------------------------------------------------------------------

#Author: Alexandre Manhaes Savio <alexsavio@gmail.com>
#Grupo de Inteligencia Computational <www.ehu.es/ccwintco>
#Universidad del Pais Vasco UPV/EHU
#
#2013, Alexandre Manhaes Savio
#Use this at your own risk!
#-------------------------------------------------------------------------------

import os
import shelve
import logging

from .filenames import (get_extension,
                        add_extension_if_needed)

log = logging.getLogger(__name__)


def save_variables_to_shelve(file_path, variables):
    """

    Parameters
    ----------
    file_path: str

    variables: dict
        Dictionary with objects. Object name -> object

    Notes
    -----
        Before calling this function, create a varlist this way:

        shelfvars = []
        for v in varnames:
            shelfvars.append(eval(v))

        #to_restore variables from shelf
        my_shelf = shelve.open(filename)
        for key in my_shelf:
           globals()[key]=my_shelf[key]
        my_shelf.close()
    """
    mashelf = shelve.open(file_path, 'n')

    for vn in variables.keys():
        try:
            mashelf[vn] = variables[vn]
        except:
            log.exception('Error shelving variable {0}'.format(vn))
            raise

    mashelf.close()


