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

import os.path as op
import logging
import array
import shutil

from   .tags import MHD_TAGS, NUMPY_TO_MHD_TYPE
from   .read import _read_meta_header

from   ..files.names import get_extension, remove_ext

log = logging.getLogger(__name__)


def write_meta_header(filename, meta_dict):
    """ Write the content of the `meta_dict` into `filename`.

    Parameters
    ----------
    filename: str
        Path to the output file

    meta_dict: dict
        Dictionary with the fields of the metadata .mhd file
    """
    header = ''
    # do not use tags = meta_dict.keys() because the order of tags matters
    for tag in MHD_TAGS:
        if tag in meta_dict.keys():
            header += '{} = {}\n'.format(tag, meta_dict[tag])

    with open(filename, 'w') as f:
        f.write(header)


def dump_raw_data(filename, data):
    """ Write the data into a raw format file. Big endian is always used.

    Parameters
    ----------
    filename: str
        Path to the output file

    data: numpy.ndarray
        n-dimensional image data array.
    """
    if data.ndim == 3:
        # Begin 3D fix
        data = data.reshape([data.shape[0], data.shape[1]*data.shape[2]])
        # End 3D fix

    a = array.array('f')
    for o in data:
        a.fromlist(list(o.flatten()))

    # if is_little_endian():
    #     a.byteswap()

    with open(filename, 'wb') as rawf:
        a.tofile(rawf)


def write_mhd_file(filename, data, shape=None, meta_dict=None):
    """ Write the `data` and `meta_dict` in two files with names
    that use `filename` as a prefix.

    Parameters
    ----------
    filename: str
        Path to the output file.
        This is going to be used as a preffix.
        Two files will be created, one with a '.mhd' extension
        and another with '.raw'. If `filename` has any of these already
        they will be taken into account to build the filenames.

    data: numpy.ndarray
        n-dimensional image data array.

    shape: tuple
        Tuple describing the shape of `data`
        Default: data.shape

    meta_dict: dict
        Dictionary with the fields of the metadata .mhd file
        Default: {}

    Returns
    -------
    mhd_filename: str
        Path to the .mhd file

    raw_filename: str
        Path to the .raw file
    """
    # check its extension
    ext = get_extension(filename)
    fname = op.basename(filename)
    if ext != '.mhd' or ext != '.raw':
        mhd_filename = fname + '.mhd'
        raw_filename = fname + '.raw'
    elif ext == '.mhd':
        mhd_filename = fname
        raw_filename = remove_ext(fname) + '.raw'
    elif ext == '.raw':
        mhd_filename = remove_ext(fname) + '.mhd'
        raw_filename = fname
    else:
        raise ValueError('`filename` extension {} from {} is not recognised. '
                         'Expected .mhd or .raw.'.format(ext, filename))

    # default values
    if meta_dict is None:
        meta_dict = {}

    if shape is None:
        shape = data.shape

    # prepare the default header
    meta_dict['ObjectType']             = meta_dict.get('ObjectType',             'Image')
    meta_dict['BinaryData']             = meta_dict.get('BinaryData',             'True' )
    meta_dict['BinaryDataByteOrderMSB'] = meta_dict.get('BinaryDataByteOrderMSB', 'False')
    meta_dict['ElementType']            = meta_dict.get('ElementType',            NUMPY_TO_MHD_TYPE[data.dtype.type])
    meta_dict['NDims']                  = meta_dict.get('NDims',                  str(len(shape)))
    meta_dict['DimSize']                = meta_dict.get('DimSize',                ' '.join([str(i) for i in shape]))
    meta_dict['ElementDataFile']        = meta_dict.get('ElementDataFile',        raw_filename)

    # target files
    mhd_filename = op.join(op.dirname(filename), mhd_filename)
    raw_filename = op.join(op.dirname(filename), raw_filename)

    # write the header
    write_meta_header(mhd_filename, meta_dict)

    # write the data
    dump_raw_data(raw_filename, data)

    return mhd_filename, raw_filename


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

    Returns
    -------
    dst: str
    """
    # check if src exists
    if not op.exists(src):
        raise IOError('Could not find file {}.'.format(src))

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
