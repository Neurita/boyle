# coding=utf-8
"""
 Data storage in different formats helper functions for data persistence.
"""
# -------------------------------------------------------------------------------
# Author: Alexandre Manhaes Savio <alexsavio@gmail.com>
# Nuklear Medizin Department
# Klinikum rechts der Isar, Technische Universitaet Muenchen
#
# 2016, Alexandre Manhaes Savio
# Use this at your own risk!
#-------------------------------------------------------------------------------

import os.path as op
from collections import OrderedDict

import numpy as np

try:
    import h5py
except:
    raise ImportError('Could not import h5py, please install it if you need it.')


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
        r   Readonly, file must exist
        r+  Read/write, file must exist
        w   Create file, truncate if exists
        w-  Create file, fail if exists
        a   Read/write if exists, create otherwise (default)

    Notes
    -----
    It is recommended to use numpy arrays as objects.
    List or tuples of strings won't work, convert them into numpy.arrays before.
    """
    if not isinstance(variables, dict):
        raise ValueError('Expected `variables` to be a dict, got a {}.'.format(type(variables)))

    if not variables:
        raise ValueError('Expected `variables` to be a non-empty dict.')

    h5file  = h5py.File(file_path, mode=mode)
    h5group = h5file.require_group(h5path)

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

    h5file.close()


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
        h5file = h5py.File(file_path, mode=mode)
    except:
        raise
    else:
        return h5file


def get_group_names(h5file, h5path='/'):
    """ Return the groups names within h5file/h5path

    Parameters
    ----------
    h5file: h5py.File or path to hdf5 file
        HDF5 file object

    h5path: str
        HDF5 group path to get the group names from

    Returns
    -------
    groupnames: list of str
        List of group names
    """
    return _get_node_names(h5file, h5path, node_type=h5py.Group)


def get_dataset_names(h5file, h5path='/'):
    """ Return all dataset names from h5path group in h5file.

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
    """ Return all datasets from h5path group in file_path.

    Parameters
    ----------
    h5file: h5py.File
        HDF5 file object

    h5path: str
        HDF5 group path to read datasets from

    Returns
    -------
    datasets: dict
        Dict with all h5py.Dataset contained in file_path/h5path
    """
    return _get_nodes(h5file, h5path, node_type=h5py.Dataset)


def extract_datasets(h5file, h5path='/'):
    """ Return all dataset contents from h5path group in h5file in an OrderedDict.

    Parameters
    ----------
    h5file: h5py.File
        HDF5 file object

    h5path: str
        HDF5 group path to read datasets from

    Returns
    -------
    datasets: OrderedDict
        Dict with variables contained in file_path/h5path
    """
    if isinstance(h5file, str):
        _h5file = h5py.File(h5file, mode='r')
    else:
        _h5file = h5file

    _datasets = get_datasets(_h5file, h5path)
    datasets  = OrderedDict()
    try:
        for ds in _datasets:
            datasets[ds.name.split('/')[-1]] = ds[:]
    except:
        raise RuntimeError('Error reading datasets in {}/{}.'.format(_h5file.filename, h5path))
    finally:
        if isinstance(h5file, str):
            _h5file.close()

    return datasets


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
    if isinstance(h5file, str):
        _h5file = get_h5file(h5file, mode='r')
    else:
        _h5file = h5file

    if not h5path.startswith('/'):
        h5path = '/' + h5path

    names = []
    try:
        h5group = _h5file.require_group(h5path)

        for node in _hdf5_walk(h5group, node_type=node_type):
            names.append(node.name)
    except:
        raise RuntimeError('Error getting node names from {}/{}.'.format(_h5file.filename, h5path))
    finally:
        if isinstance(h5file, str):
            _h5file.close()

    return names


def _get_nodes(h5file, h5path='/', node_type=h5py.Dataset):
    """ Return the nodes within h5path of the h5file.

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
    if isinstance(h5file, str):
        _h5file = get_h5file(h5file, mode='r')
    else:
        _h5file = h5file

    if not h5path.startswith('/'):
        h5path = '/' + h5path

    names = []
    try:
        h5group = _h5file.require_group(h5path)

        for node in _hdf5_walk(h5group, node_type=node_type):
            names.append(node)
    except:
        raise RuntimeError('Error getting {} nodes from {}/{}.'.format(str(node_type), _h5file.filename, h5path))
    finally:
        if isinstance(h5file, str):
            _h5file.close()

    return names
