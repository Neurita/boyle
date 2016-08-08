# coding=utf-8
# -------------------------------------------------------------------------------
# Author: Alexandre Manhaes Savio <alexsavio@gmail.com>
# Author: Oier Echaniz
# Grupo de Inteligencia Computational <www.ehu.es/ccwintco>
# Universidad del Pais Vasco UPV/EHU
#
# 2015, Alexandre Manhaes Savio
# Use this at your own risk!
# -------------------------------------------------------------------------------

import array
import os.path      as      op
import numpy        as      np
from   functools    import  reduce

from   .tags        import  MHD_TAGS, MHD_TO_NUMPY_TYPE, NDARRAY_TO_ARRAY_TYPE


def _read_meta_header(filename):
    """Return a dictionary of meta data from meta header file.

    Parameters
    ----------
    filename: str
        Path to a .mhd file

    Returns
    -------
    meta_dict: dict
        A dictionary with the .mhd header content.
    """
    fileIN = open(filename, 'r')
    line   = fileIN.readline()

    meta_dict = {}
    tag_flag = [False]*len(MHD_TAGS)
    while line:
        tags = str.split(line, '=')
        # print tags[0]
        for i in range(len(MHD_TAGS)):
            tag = MHD_TAGS[i]
            if (str.strip(tags[0]) == tag) and (not tag_flag[i]):
                # print tags[1]
                meta_dict[tag] = str.strip(tags[1])
                tag_flag[i] = True
        line = fileIN.readline()
    #  comment
    fileIN.close()
    return meta_dict


def load_raw_data_with_mhd(filename):
    """Return a dictionary of meta data from meta header file.

    Parameters
    ----------
    filename: str
        Path to a .mhd file

    Returns
    -------
    data: numpy.ndarray
        n-dimensional image data array.

    meta_dict: dict
        A dictionary with the .mhd header content.
    """
    meta_dict = _read_meta_header(filename)
    dim       = int(meta_dict['NDims'])

    assert (meta_dict['ElementType'] in MHD_TO_NUMPY_TYPE)

    arr = [int(i) for i in meta_dict['DimSize'].split()]
    volume = reduce(lambda x, y: x*y, arr[0:dim-1], 1)

    pwd       = op.dirname(filename)
    raw_file  = meta_dict['ElementDataFile']
    data_file = op.join(pwd, raw_file)

    ndtype    = MHD_TO_NUMPY_TYPE[meta_dict['ElementType']]
    arrtype   = NDARRAY_TO_ARRAY_TYPE[ndtype]

    with open(data_file, 'rb') as fid:
        binvalues = array.array(arrtype)
        binvalues.fromfile(fid, volume*arr[dim-1])

    data = np.array  (binvalues, ndtype)
    data = np.reshape(data, (arr[dim-1], volume))

    if dim >= 3:
        # Begin 3D fix
        dimensions = [int(i) for i in meta_dict['DimSize'].split()]
        # dimensions.reverse() ??
        data       = data.reshape(dimensions)
        # End 3D fix

    return data, meta_dict


def get_3D_from_4D(filename, vol_idx=0):
    """Return a 3D volume from a 4D nifti image file

    Parameters
    ----------
    filename: str
        Path to the 4D .mhd file

    vol_idx: int
        Index of the 3D volume to be extracted from the 4D volume.

    Returns
    -------
    vol, hdr
        The data array and the new 3D image header.
    """
    def remove_4th_element_from_hdr_string(hdr, fieldname):
        if fieldname in hdr:
            hdr[fieldname] = ' '.join(hdr[fieldname].split()[:3])

    vol, hdr = load_raw_data_with_mhd(filename)

    if vol.ndim != 4:
        raise ValueError('Volume in {} does not have 4 dimensions.'.format(op.join(op.dirname(filename),
                                                                                   hdr['ElementDataFile'])))

    if not 0 <= vol_idx < vol.shape[3]:
        raise IndexError('IndexError: 4th dimension in volume {} has {} volumes, not {}.'.format(filename,
                                                                                                 vol.shape[3], vol_idx))

    new_vol = vol[:, :, :, vol_idx].copy()

    hdr['NDims'] = 3
    remove_4th_element_from_hdr_string(hdr, 'ElementSpacing')
    remove_4th_element_from_hdr_string(hdr, 'DimSize')

    return new_vol, hdr
