# coding=utf-8
# -------------------------------------------------------------------------------

# Author: Alexandre Manhaes Savio <alexsavio@gmail.com>
# Grupo de Inteligencia Computational <www.ehu.es/ccwintco>
# Universidad del Pais Vasco UPV/EHU
#
# 2013, Alexandre Manhaes Savio
# Use this at your own risk!
#-------------------------------------------------------------------------------

import os
import shelve
import logging
import h5py
import os.path  as op
import scipy.io as sio
import numpy    as np
import pandas   as pd

from .files.names import (get_extension,
                          add_extension_if_needed)

log = logging.getLogger(__name__)


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
        except:
            log.exception('Error shelving variable {0}'.format(vn))
            raise

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
    except:
        log.exception('Error saving to {}'.format(file_path))
        raise


def save_variables_to_hdf5(file_path, variables, mode='w', h5path='/'):
    """
    Parameters
    ----------
    file_path: str

    variables: dict
        Dictionary with objects. Object name -> object

    mode: str
        HDF5 file access mode
        See h5py documentation for details.
        Most used here:
        'r+' for read/write
        'w' for destroying then writing

    Notes
    -----
    It is recommended to use numpy arrays as objects.
    List or tuples of strings won't work, convert them into numpy.arrays before.
    """
    if not isinstance(variables, dict):
        raise ValueError('Expected argument variables to be a dict, got a {}.'.format(type(variables)))

    h5file  = h5py.File(file_path, mode=mode)
    h5group = h5file.require_group(h5path)

    try:
        for vn in variables:
            data = variables[vn]

            # fix for string numpy arrays
            if hasattr(data, 'dtype') and (data.dtype.type is np.string_ or data.dtype.type is np.unicode_):
                dt   = h5py.special_dtype(vlen=str)
                data = data.astype(dt)

            if isinstance(data, dict):
                for key in data:
                    #h5group.create_dataset(str(key))
                    #import ipdb
                    #ipdb.set_trace()
                    h5group[str(key)] = data[key]

            elif isinstance(data, list):
                for idx, item in enumerate(data):
                    #h5group.create_dataset(str(idx))
                    h5group[str(idx)] = item
            else:
                h5group[vn] = data
    except:
        log.exception('Error saving {0} in {1}'.format(vn, file_path))
        raise
    finally:
        h5file.close()


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
            save_variables_to_hdf5(output_file, variables)

        else:
            log.error('Filename extension {0} not accepted.'.format(ext))

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


# -------------------------------------------------------------------------
# HDF5 helpers
# -------------------------------------------------------------------------
def get_h5file(file_path, mode='r'):
    """ Return the h5py.File given its file path.

    Parameters
    ----------
    file_path: string
        HDF5 file path

    mode: string
        r   Readonly, file must exist
        r+  Read/write, file must exist
        w   Create file, truncate if exists
        w-  Create file, fail if exists
        a   Read/write if exists, create otherwise (default)

    Returns
    -------
    h5file: h5py.File
    """
    if not op.exists(file_path):
        raise IOError('Could not find file {}.'.format(file_path))

    try:
        h5file  = h5py.File(file_path, mode=mode)
    except:
        raise
    else:
        return h5file


def get_group_names(h5file, h5path='/'):
    """ Return the groups names within h5file/h5path

    Parameters
    ----------
    h5file: h5py.File
        HDF5 file object

    h5path: str
        HDF5 group path to get the group names from

    Returns
    -------
    gnames: list of str
        List of group names
    """
    return _get_node_names(h5file, h5path, node_type=h5py.Group)


def get_dataset_names(h5file, h5path='/'):
    """
    Returns all dataset names from h5path group in h5file.

    Parameters
    ----------
    h5file: h5py.File
        HDF5 file object

    h5path: str
        HDF5 group path to read datasets from

    Returns
    -------
    dsnames: list of str
        List of dataset names contained in h5file/h5path
    """
    return _get_node_names(h5file, h5path, node_type=h5py.Dataset)


def get_datasets(h5file, h5path='/'):
    """
    Returns all datasets from h5path group in file_path.

    Parameters
    ----------
    h5file: h5py.File
        HDF5 file object

    h5path: str
        HDF5 group path to read datasets from

    Returns
    -------
    datasets: dict
        Dict with variables contained in file_path/h5path
    """
    return _get_nodes(h5file, h5path, node_type=h5py.Dataset)


def _hdf5_walk(group, node_type=h5py.Dataset):
    for node in list(group.values()):
        if isinstance(node, node_type):
            yield node


def _get_node_names(h5file, h5path='/', node_type=h5py.Dataset):
    """Return the node of type node_type names within h5path of h5file.

    Parameters
    ----------
    h5file: h5py.File
        HDF5 file object

    h5path: str
        HDF5 group path to get the group names from

    node_type: h5py object type
        HDF5 object type

    Returns
    -------
    names: list of str
        List of names
    """
    names = []
    try:
        h5group = h5file.require_group(h5path)

        for node in _hdf5_walk(h5group, node_type=node_type):
            names.append(node.name)
    except:
        raise
    else:
        return names


def _get_nodes(h5file, h5path='/', node_type=h5py.Dataset):
    """ Returns the nodes within h5path of the h5file.

    Parameters
    ----------
    h5file: h5py.File
        HDF5 file object

    h5path: str
        HDF5 group path to get the nodes from

    node_type: h5py object type
        The type of the nodes that you want to get

    Returns
    -------
    nodes: list of node_type objects
    """
    names = []
    try:
        h5group = h5file.require_group(h5path)

        for node in _hdf5_walk(h5group, node_type=node_type):
            names.append(node)
    except:
        raise
    else:
        return names
