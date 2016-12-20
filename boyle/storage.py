"""
 Data storage in different formats helper functions for data persistence.
"""
# coding=utf-8
# -------------------------------------------------------------------------------

# Author: Alexandre Manhaes Savio <alexsavio@gmail.com>
# Grupo de Inteligencia Computational <www.ehu.es/ccwintco>
# Universidad del Pais Vasco UPV/EHU
#
# 2013, Alexandre Manhaes Savio
# Use this at your own risk!
#-------------------------------------------------------------------------------

import shelve
import scipy.io    as sio
import pandas      as pd

from .files.names import (get_extension,
                          add_extension_if_needed)


def sav_to_pandas_rpy2(input_file):
    """
    SPSS .sav files to Pandas DataFrame through Rpy2

    :param input_file: string

    :return:
    """
    import pandas.rpy.common as com

    w = com.robj.r('foreign::read.spss("%s", to.data.frame=TRUE)' % input_file)
    return com.convert_robj(w)


def sav_to_pandas_savreader(input_file):
    """
    SPSS .sav files to Pandas DataFrame through savreader module

    :param input_file: string

    :return:
    """
    from savReaderWriter import SavReader
    lines = []
    with SavReader(input_file, returnHeader=True) as reader:
        header = next(reader)
        for line in reader:
            lines.append(line)

    return pd.DataFrame(data=lines, columns=header)


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
        except KeyError as ke:
            raise Exception('Error shelving variable {0}'.format(vn)) from ke

    mashelf.close()


def save_variables_to_mat(file_path, variables, format='5'):
    """

    Parameters
    ---------
    file_path: str

    variables: dict
        Dictionary with objects. Object name -> object

    format : {'5', '4'}, string, optional
        '5' (the default) for MATLAB 5 and up (to 7.2),
        '4' for MATLAB 4 .mat files
        See scipy.io.savemat dostrings.
    """

    try:
        sio.savemat(file_path, variables, format=format)
    except IOError as ioe:
        raise IOError('Error saving to {}'.format(file_path)) from ioe


class ExportData(object):

    def __init__(self):
        pass

    @staticmethod
    def save_variables(filename, variables):
        """Save given variables in a file.
        Valid extensions: '.pyshelf' or '.shelf' (Python shelve)
                          '.mat' (Matlab archive),
                          '.hdf5' or '.h5' (HDF5 file)

        Parameters
        ----------
        filename: str
            Output file path.

        variables: dict
            Dictionary varname -> variable

        Raises
        ------
        ValueError: if the extension of the filesname is not recognized.
        """
        ext = get_extension(filename).lower()
        out_exts = {'.pyshelf', '.shelf', '.mat', '.hdf5', '.h5'}

        output_file = filename
        if not ext in out_exts:
            output_file = add_extension_if_needed(filename, '.pyshelf')
            ext = get_extension(filename)

        if ext == '.pyshelf' or ext == '.shelf':
            save_variables_to_shelve(output_file, variables)

        elif ext == '.mat':
            save_variables_to_mat(output_file, variables)

        elif ext == '.hdf5' or ext == '.h5':
            from .hdf5 import save_variables_to_hdf5
            save_variables_to_hdf5(output_file, variables)

        else:
            raise ValueError('Filename extension {0} not accepted.'.format(ext))

    @staticmethod
    def save_varlist(filename, varnames, varlist):
        """
        Valid extensions '.pyshelf', '.mat', '.hdf5' or '.h5'

        @param filename: string

        @param varnames: list of strings
        Names of the variables

        @param varlist: list of objects
        The objects to be saved
        """
        variables = {}
        for i, vn in enumerate(varnames):
            variables[vn] = varlist[i]

        ExportData.save_variables(filename, variables)

