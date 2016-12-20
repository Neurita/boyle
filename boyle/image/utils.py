# coding=utf-8
"""
Utilities to wrap boyle for the base classes of the image submodule.
"""
# ------------------------------------------------------------------------------
# Author: Alexandre Manhaes Savio <alexsavio@gmail.com>
# Klinikum rechts der Isar, TUM, Munich
#
# 2016, Alexandre Manhaes Savio
# Use this at your own risk!
# ------------------------------------------------------------------------------

import gc
import os.path              as op

import numpy                as np
import nibabel              as nib
from   six                  import string_types

from   ..files.names         import get_extension

from   ..nifti.neuroimage    import NiftiImage
from   ..mhd.read            import load_raw_data_with_mhd

from   ..nifti.read          import get_data
from   ..nifti.check         import check_img_compatibility, repr_imgs, is_img, _make_it_3d
from   ..nifti.mask          import load_mask, _apply_mask_to_4d_data, vector_to_volume, matrix_to_4dvolume
from   ..nifti.smooth        import _smooth_data_array
from   ..nifti.storage       import save_niigz


def open_volume_file(filepath):
    """Open a volumetric file using the tools following the file extension.

    Parameters
    ----------
    filepath: str
        Path to a volume file

    Returns
    -------
    volume_data: np.ndarray
        Volume data

    pixdim: 1xN np.ndarray
        Vector with the description of the voxels physical size (usually in mm) for each volume dimension.

    Raises
    ------
    IOError
        In case the file is not found.
    """
    # check if the file exists
    if not op.exists(filepath):
        raise IOError('Could not find file {}.'.format(filepath))

    # define helper functions
    def open_nifti_file(filepath):
        return NiftiImage(filepath)

    def open_mhd_file(filepath):
        return MedicalImage(filepath)
        vol_data, hdr_data = load_raw_data_with_mhd(filepath)
        # TODO: convert vol_data and hdr_data into MedicalImage
        return vol_data, hdr_data

    def open_mha_file(filepath):
        raise NotImplementedError('This function has not been implemented yet.')

    # generic loader function
    def _load_file(filepath, loader):
        return loader(filepath)

    # file_extension -> file loader function
    filext_loader = {
                    'nii': open_nifti_file,
                    'mhd': open_mhd_file,
                    'mha': open_mha_file,
                    }

    # get extension of the `filepath`
    ext = get_extension(filepath)

    # find the loader from `ext`
    loader = None
    for e in filext_loader:
        if ext in e:
            loader = filext_loader[e]

    if loader is None:
        raise ValueError('Could not find a loader for file {}.'.format(filepath))

    return _load_file(filepath, loader)


def _check_medimg(image, make_it_3d=True):
    """Check that image is a proper img. Turn filenames into objects.

    Parameters
    ----------
    image: img-like object or str
        Can either be:
        - a file path to a medical image file, e.g. NifTI, .mhd/raw, .mha
        - any object with get_data() method and affine & header attributes, e.g., nibabel.Nifti1Image.
        - a Numpy array, which will be wrapped by a nibabel.Nifti2Image class with an `eye` affine.
        If niimg is a string, consider it as a path to Nifti image and
        call nibabel.load on it. If it is an object, check if get_data()
        and get_affine() methods are present, raise TypeError otherwise.

    make_it_3d: boolean, optional
        If True, check if the image is a 3D image and raise an error if not.

    Returns
    -------
    result: nifti-like
       result can be nibabel.Nifti1Image or the input, as-is. It is guaranteed
       that the returned object has get_data() and get_affine() methods.
    """
    if isinstance(image, string_types):
        # a filename, load it
        img = open_volume_file(image)

        if make_it_3d:
            img = _make_it_3d(img)

        return img

    elif isinstance(image, np.array):
        return nib.Nifti2Image(image, affine=np.eye(image.ndim + 1))

    elif isinstance(image, nib.Nifti1Image) or is_img(image):
        return image

    else:
        raise TypeError('Data given cannot be converted to a medical image'
                        ' image: this object -"{}"- does not have'
                        ' get_data or get_affine methods'.format(type(image)))

