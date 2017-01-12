# coding=utf-8
"""
Helper functions to convert DICOM files to other formats.
"""
# ------------------------------------------------------------------------------
# Author: Alexandre Manhaes Savio <alexsavio@gmail.com>
#
# 2015, Alexandre Manhaes Savio
# Use this at your own risk!
# ------------------------------------------------------------------------------

import os
import os.path as op
import logging
import tempfile
import subprocess
from   glob import glob

import dicom
import nibabel
import numpy

from   ..files.utils import copy_w_ext, copy_w_plus
from   ..files.names import remove_ext


log = logging.getLogger(__name__)


def generate_config(output_directory):
    """ Generate a dcm2nii configuration file that disable the interactive
    mode.
    """
    if not op.isdir(output_directory):
        os.makedirs(output_directory)

    config_file = op.join(output_directory, "config.ini")
    open_file = open(config_file, "w")
    open_file.write("[BOOL]\nManualNIfTIConv=0\n")
    open_file.close()
    return config_file


def add_meta_to_nii(nii_file, dicom_file, dcm_tags=''):
    """ Add slice duration and acquisition times to the headers of the nifit1 files in `nii_file`.
    It will add the repetition time of the DICOM file (field: {0x0018, 0x0080, DS, Repetition Time})
    to the NifTI file as well as any other tag in `dcm_tags`.
    All selected DICOM tags values are set in the `descrip` nifti header field.
    Note that this will modify the header content of `nii_file`.

    Parameters
    ----------
    nii_files: str
        Path to the NifTI file to modify.

    dicom_file: str
        Paths to the DICOM file from where to get the meta data.

    dcm_tags: list of str
        List of tags from the DICOM file to read and store in the nifti file.
    """
    # Load a dicom image
    dcmimage = dicom.read_file(dicom_file)

    # Load the nifti1 image
    image = nibabel.load(nii_file)

    # Check the we have a nifti1 format image
    if not isinstance(image, nibabel.nifti1.Nifti1Image):
        raise Exception(
            "Only Nifti1 image are supported not '{0}'.".format(
                type(image)))

    # check if dcm_tags is one string, if yes put it in a list:
    if isinstance(dcm_tags, str):
        dcm_tags = [dcm_tags]

    # Fill the nifti1 header
    header = image.get_header()

    # slice_duration: Time for 1 slice
    repetition_time = float(dcmimage[("0x0018", "0x0080")].value)
    header.set_dim_info(slice=2)
    nb_slices = header.get_n_slices()
    # Force round to 0 digit after coma. If more, nibabel completes to
    # 6 digits with random numbers...
    slice_duration = round(repetition_time / nb_slices, 0)
    header.set_slice_duration(slice_duration)

    # add free dicom fields
    if dcm_tags:
        content = ["{0}={1}".format(name, dcmimage[tag].value)
                   for name, tag in dcm_tags]
        free_field = numpy.array(";".join(content),
                                 dtype=header["descrip"].dtype)
        image.get_header()["descrip"] = free_field

    # Update the image header
    image.update_header()

    # Save the filled image
    nibabel.save(image, nii_file)


def call_dcm2nii(work_dir, arguments=''):
    """Converts all DICOM files within `work_dir` into one or more
    NifTi files by calling dcm2nii on this folder.

    Parameters
    ----------
    work_dir: str
        Path to the folder that contain the DICOM files

    arguments: str
        String containing all the flag arguments for `dcm2nii` CLI.

    Returns
    -------
    sys_code: int
        dcm2nii execution return code
    """
    if not op.exists(work_dir):
        raise IOError('Folder {} not found.'.format(work_dir))

    cmd_line = 'dcm2nii {0} "{1}"'.format(arguments, work_dir)
    log.info(cmd_line)
    return subprocess.check_call(cmd_line, shell=True)


def convert_dcm2nii(input_dir, output_dir, filename):
    """ Call MRICron's `dcm2nii` to convert the DICOM files inside `input_dir`
    to Nifti and save the Nifti file in `output_dir` with a `filename` prefix.

    Parameters
    ----------
    input_dir: str
        Path to the folder that contains the DICOM files

    output_dir: str
        Path to the folder where to save the NifTI file

    filename: str
        Output file basename

    Returns
    -------
    filepaths: list of str
        List of file paths created in `output_dir`.
    """
    # a few checks before doing the job
    if not op.exists(input_dir):
        raise IOError('Expected an existing folder in {}.'.format(input_dir))

    if not op.exists(output_dir):
        raise IOError('Expected an existing output folder in {}.'.format(output_dir))

    # create a temporary folder for dcm2nii export
    tmpdir = tempfile.TemporaryDirectory(prefix='dcm2nii_')

    # call dcm2nii
    arguments = '-o "{}" -i y'.format(tmpdir.name)
    try:
        call_out = call_dcm2nii(input_dir, arguments)
    except:
        raise
    else:
        log.info('Converted "{}" to nifti.'.format(input_dir))

        # get the filenames of the files that dcm2nii produced
        filenames  = glob(op.join(tmpdir.name, '*.nii*'))

        # cleanup `filenames`, using only the post-processed (reoriented, cropped, etc.) images by dcm2nii
        cleaned_filenames = remove_dcm2nii_underprocessed(filenames)

        # copy files to the output_dir
        filepaths = []
        for srcpath in cleaned_filenames:
            dstpath = op.join(output_dir, filename)
            realpath = copy_w_plus(srcpath, dstpath)
            filepaths.append(realpath)

            # copy any other file produced by dcm2nii that is not a NifTI file, e.g., *.bvals, *.bvecs, etc.
            basename = op.basename(remove_ext(srcpath))
            aux_files = set(glob(op.join(tmpdir.name, '{}.*'     .format(basename)))) - \
                        set(glob(op.join(tmpdir.name, '{}.nii*'.format(basename))))
            for aux_file in aux_files:
                aux_dstpath = copy_w_ext(aux_file, output_dir, remove_ext(op.basename(realpath)))
                filepaths.append(aux_dstpath)

        return filepaths


def remove_dcm2nii_underprocessed(filepaths):
    """ Return a subset of `filepaths`. Keep only the files that have a basename longer than the
    others with same suffix.
    This works based on that dcm2nii appends a preffix character for each processing
    step it does automatically in the DICOM to NifTI conversion.

    Parameters
    ----------
    filepaths: iterable of str

    Returns
    -------
    cleaned_paths: iterable of str
    """
    cln_flist = []

    # sort them by size
    len_sorted = sorted(filepaths, key=len)

    for idx, fpath in enumerate(len_sorted):
        remove = False

        # get the basename and the rest of the files
        fname = op.basename(fpath)
        rest  = len_sorted[idx+1:]

        # check if the basename is in the basename of the rest of the files
        for rest_fpath in rest:
            rest_file = op.basename(rest_fpath)
            if rest_file.endswith(fname):
                remove = True
                break

        if not remove:
            cln_flist.append(fpath)

    return cln_flist
