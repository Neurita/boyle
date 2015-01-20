# -*- coding: utf-8 -*-
# ======================================================================
# Program:   Diffusion Weighted MRI Reconstruction
# Module:    $RCSfile: mhd_utils.py,v $
# Language:  Python
# Author:    $Author: bjian $
# Date:      $Date: 2008/10/27 05:55:55 $
# Version:   $Revision: 1.2 $
# Last Edited by alexsavio and oiertwo 2014/11/10
# ======================================================================

import os
import os.path as op
import logging
import numpy as np
import array
import shutil
from   functools import reduce

from   .files.names import get_extension, remove_ext


log = logging.getLogger(__name__)


# the order of these tags matter
MHD_TAGS = ['ObjectType',
            'NDims',
            'BinaryData',
            'BinaryDataByteOrderMSB',
            'CompressedData',
            'CompressedDataSize',
            'TransformMatrix',
            'Offset',
            'CenterOfRotation',
            'AnatomicalOrientation',
            'ElementSpacing',
            'DimSize',
            'ElementType',
            'ElementDataFile',
            'Comment',
            'SeriesDescription',
            'AcquisitionDate',
            'AcquisitionTime',
            'StudyDate',
            'StudyTime']


MHD_TO_NUMPY_TYPE   = {'MET_FLOAT' : np.float,
                       'MET_UCHAR' : np.uint8,
                       'MET_CHAR'  : np.int8,
                       'MET_USHORT': np.uint8,
                       'MET_SHORT' : np.int8,
                       'MET_UINT'  : np.uint32,
                       'MET_INT'   : np.int32,
                       'MET_ULONG' : np.uint64,
                       'MET_ULONG' : np.int64,
                       'MET_FLOAT' : np.float32,
                       'MET_DOUBLE': np.float64}


NDARRAY_TO_ARRAY_TYPE = {np.float  : 'f',
                         np.uint8  : 'H',
                         np.int8   : 'h',
                         np.uint16 : 'I',
                         np.int16  : 'i',
                         np.uint32 : 'I',
                         np.int32  : 'i',
                         np.uint64 : 'I',
                         np.int64  : 'i',
                         np.float32: 'f',
                         np.float64: 'd',}


NUMPY_TO_MHD_TYPE = {v: k for k, v in MHD_TO_NUMPY_TYPE.items()}
# ARRAY_TO_NDARRAY_TYPE = {v: k for k, v in NDARRAY_TO_ARRAY_TYPE.items()}


def read_meta_header(filename):
    """Return a dictionary of meta data from meta header file"""
    fileIN = open(filename, "r")
    line = fileIN.readline()

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
    meta_dict = read_meta_header(filename)
    dim       = int(meta_dict['NDims'])

    assert(meta_dict['ElementType'] in MHD_TO_NUMPY_TYPE)

    arr = [int(i) for i in meta_dict['DimSize'].split()]
    volume = reduce(lambda x, y: x*y, arr[0:dim-1], 1)

    pwd = op.dirname(filename)
    raw_file = meta_dict['ElementDataFile']
    data_file = op.join(pwd, raw_file)

    ndtype  = MHD_TO_NUMPY_TYPE[meta_dict['ElementType']]
    arrtype = NDARRAY_TO_ARRAY_TYPE[ndtype]

    with open(data_file, 'rb') as fid:
        binvalues = array.array(arrtype)
        binvalues.fromfile(fid, volume*arr[dim-1])

    data = np.array  (binvalues, ndtype)
    data = np.reshape(data, (arr[dim-1], volume))

    if dim == 3:
        # Begin 3D fix
        dimensions = [int(i) for i in meta_dict['DimSize'].split()]
        dimensions.reverse()
        data = data.reshape(dimensions)
        # End 3D fix

    return (data, meta_dict)


def write_meta_header(filename, meta_dict):
    header = ''
    # do not use tags = meta_dict.keys() because the order of tags matters
    for tag in MHD_TAGS:
        if tag in meta_dict.keys():
            header += '{} = {}\n'.format(tag, meta_dict[tag])
    f = open(filename, 'w')
    f.write(header)
    f.close()


def dump_raw_data(filename, data):
    """ Write the data into a raw format file. Big endian is always used. """
    if data.ndim == 3:
        # Begin 3D fix
        data = data.reshape([data.shape[0], data.shape[1]*data.shape[2]])
        # End 3D fix

    rawfile = open(filename, 'wb')
    a = array.array('f')
    for o in data:
        a.fromlist(list(o))
    # if is_little_endian():
    #     a.byteswap()
    a.tofile(rawfile)
    rawfile.close()


def write_mhd_file(filename, data, shape, meta_dict={}):
    # check its extension
    ext = get_extension(src)
    if ext != '.mhd' or ext != '.raw':
        mhd_filename = filename + '.mhd'
        raw_filename = filename + '.raw'
    elif ext == '.mhd':
        mhd_filename = filename
        raw_filename = remove_ext(filename) + '.raw'
    elif ext == '.raw':
        mhd_filename = remove_ext(filename) + '.mhd'
        raw_filename = filename

    meta_dict['ObjectType']             = meta_dict.get('ObjectType',             'Image')
    meta_dict['BinaryData']             = meta_dict.get('BinaryData',             'True' )
    meta_dict['BinaryDataByteOrderMSB'] = meta_dict.get('BinaryDataByteOrderMSB', 'False')
    meta_dict['ElementType']            = meta_dict.get('ElementType',            NUMPY_TO_MHD_TYPE[data.dtype])
    meta_dict['NDims']                  = meta_dict.get('NDims',                  str(len(shape)))
    meta_dict['DimSize']                = meta_dict.get('DimSize',                ' '.join([str(i) for i in shape]))
    meta_dict['ElementDataFile']        = meta_dict.get('ElementDataFile',        raw_filename)
    write_meta_header(mhd_filename, meta_dict)

    pwd = os.path.split(filename)[0]
    if pwd:
        data_file = op.join(pwd, meta_dict['ElementDataFile'])
    else:
        data_file = meta_dict['ElementDataFile']

    dump_raw_data(data_file, data)


def copy_mhd_and_raw(src, dst):
    """Copy .mhd and .raw files to dst.

    If dst is a folder, won't change the file, but if dst is another filepath,
    will modify the ElementDataFile field in the .mhd to point to the
    new renamed .raw file.

    Parameters
    ----------
    src: str
        Path to the .mhd file to be copied

    dst: str
        Path to the destination of the .mhd and .raw files.
        If a new file name is given, the extension will be ignored.
    """
    # check if src exists
    if not op.exists(src):
        msg = 'Could not find file {}.'.format(src)
        log.error(msg)
        raise IOError(msg)

    # check its extension
    ext = get_extension(src)
    if ext != '.mhd':
        msg = 'The src file path must be a .mhd file. Given: {}.'.format(src)
        log.error(msg)
        raise ValueError(msg)

    # get the raw file for this src mhd file
    meta_src = read_meta_header(src)

    # get the source raw file
    src_raw = meta_src['ElementDataFile']
    if not op.isabs(src_raw):
        src_raw = op.join(op.dirname(src), src_raw)

    # check if dst is dir
    if op.isdir(dst):
        # copy the mhd and raw file to its destiny
        shutil.copyfile(src, dst)
        shutil.copyfile(src_raw, dst)
        return dst

    # build raw file dst file name
    dst_raw = op.join(op.dirname(dst), remove_ext(op.basename(dst))) + '.raw'

    # add extension to the dst path
    if get_extension(dst) != '.mhd':
        dst += '.mhd'

    # copy the mhd and raw file to its destiny
    log.debug('cp: {} -> {}'.format(src,     dst))
    log.debug('cp: {} -> {}'.format(src_raw, dst_raw))
    shutil.copyfile(src, dst)
    shutil.copyfile(src_raw, dst_raw)

    # check if src file name is different than dst file name
    # if not the same file name, change the content of the ElementDataFile field
    if op.basename(dst) != op.basename(src):
        log.debug('modify {}: ElementDataFile: {} -> {}'.format(dst, src_raw,
                                                                op.basename(dst_raw)))
        meta_dst = read_meta_header(dst)
        meta_dst['ElementDataFile'] = op.basename(dst_raw)
        write_meta_header(dst, meta_dst)

    return dst



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

    vol, hdr = load_raw_data_with_mhd(nii_file)

    if vol.ndim != 4:
        msg = 'Volume in {} does not have 4 dimensions.'.format(nii_file)
        log.error(msg)
        raise ValueError(msg)

    if not 0 < vol_idx < vol.shape[3]:
        msg = 'IndexError: 4th dimension in volume {} has {} volumes, not {}.'.format(nii_file, vol.shape[3], vol_idx)
        log.error(msg)
        raise IndexError(msg)

    new_vol = vol[:, :, :, vol_idx].copy()

    hdr['NDims'] = 3
    remove_4th_element_from_hdr_string(hdr, 'ElementSpacing')
    remove_4th_element_from_hdr_string(hdr, 'DimSize')

    return new_vol, hdr
