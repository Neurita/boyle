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


import os
import os.path as op
import logging
import array
import shutil

from   .tags import MHD_TAGS, NUMPY_TO_MHD_TYPE
from   .read import _read_meta_header

from   ..files.names import get_extension, remove_ext

log = logging.getLogger(__name__)


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
    ext = get_extension(filename)
    if ext != '.mhd' or ext != '.raw':
        mhd_filename = filename + '.mhd'
        raw_filename = filename + '.raw'
    elif ext == '.mhd':
        mhd_filename = filename
        raw_filename = remove_ext(filename) + '.raw'
    elif ext == '.raw':
        mhd_filename = remove_ext(filename) + '.mhd'
        raw_filename = filename
    else:
        raise ValueError('`filename` extension {} from {} is not recognised. '
                         'Expected .mhd or .raw.'.format(ext, filename))

    meta_dict['ObjectType']             = meta_dict.get('ObjectType',             'Image')
    meta_dict['BinaryData']             = meta_dict.get('BinaryData',             'True' )
    meta_dict['BinaryDataByteOrderMSB'] = meta_dict.get('BinaryDataByteOrderMSB', 'False')
    meta_dict['ElementType']            = meta_dict.get('ElementType',            NUMPY_TO_MHD_TYPE[data.dtype.type])
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
        raise IOError(msg)

    # check its extension
    ext = get_extension(src)
    if ext != '.mhd':
        msg = 'The src file path must be a .mhd file. Given: {}.'.format(src)
        raise ValueError(msg)

    # get the raw file for this src mhd file
    meta_src = _read_meta_header(src)

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
        meta_dst = _read_meta_header(dst)
        meta_dst['ElementDataFile'] = op.basename(dst_raw)
        write_meta_header(dst, meta_dst)

    return dst
