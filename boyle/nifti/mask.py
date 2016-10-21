# coding=utf-8
"""
Utilities to compute/apply masking from Nifti images
"""
# ------------------------------------------------------------------------------
# Author: Alexandre Manhaes Savio <alexsavio@gmail.com>
# Wrocław University of Technology
#
# 2015, Alexandre Manhaes Savio
# Use this at your own risk!
# ------------------------------------------------------------------------------
import logging as log
import numpy   as np
import nibabel as nib

from .read              import get_img_data
from ..exceptions       import NiftiFilesNotCompatible
from .check             import (are_compatible_imgs, check_img, repr_imgs,
                                check_img_compatibility, get_data)
from ..utils.numpy_conversions  import as_ndarray


def load_mask(image, allow_empty=True):
    """Load a Nifti mask volume.

    Parameters
    ----------
    image: img-like object or boyle.nifti.NeuroImage or str
        Can either be:
        - a file path to a Nifti image
        - any object with get_data() and get_affine() methods, e.g., nibabel.Nifti1Image.
        If niimg is a string, consider it as a path to Nifti image and
        call nibabel.load on it. If it is an object, check if get_data()
        and get_affine() methods are present, raise TypeError otherwise.

    allow_empty: boolean, optional
        Allow loading an empty mask (full of 0 values)

    Returns
    -------
    nibabel.Nifti1Image with boolean data.
    """
    img    = check_img(image, make_it_3d=True)
    values = np.unique(img.get_data())

    if len(values) == 1:
        # We accept a single value if it is not 0 (full true mask).
        if values[0] == 0 and not allow_empty:
            raise ValueError('Given mask is invalid because it masks all data')

    elif len(values) == 2:
        # If there are 2 different values, one of them must be 0 (background)
        if 0 not in values:
            raise ValueError('Background of the mask must be represented with 0.'
                             ' Given mask contains: {}.'.format(values))

    elif len(values) != 2:
        # If there are more than 2 values, the mask is invalid
            raise ValueError('Given mask is not made of 2 values: {}. '
                             'Cannot interpret as true or false'.format(values))

    return nib.Nifti1Image(as_ndarray(get_img_data(img), dtype=bool), img.get_affine(), img.get_header())


def load_mask_data(image, allow_empty=True):
    """Load a Nifti mask volume and return its data matrix as boolean and affine.

    Parameters
    ----------
    image: img-like object or boyle.nifti.NeuroImage or str
        Can either be:
        - a file path to a Nifti image
        - any object with get_data() and get_affine() methods, e.g., nibabel.Nifti1Image.
        If niimg is a string, consider it as a path to Nifti image and
        call nibabel.load on it. If it is an object, check if get_data()
        and get_affine() methods are present, raise TypeError otherwise.

    allow_empty: boolean, optional
        Allow loading an empty mask (full of 0 values)

    Returns
    -------
    numpy.ndarray with dtype==bool, numpy.ndarray of affine transformation
    """
    mask = load_mask(image, allow_empty=allow_empty)
    return get_img_data(mask), mask.get_affine()


def binarise(image, threshold=0):
    """Binarise image with the given threshold

    Parameters
    ----------
    image: img-like object or boyle.nifti.NeuroImage or str
        Can either be:
        - a file path to a Nifti image
        - any object with get_data() and get_affine() methods, e.g., nibabel.Nifti1Image.
        If niimg is a string, consider it as a path to Nifti image and
        call nibabel.load on it. If it is an object, check if get_data()
        and get_affine() methods are present, raise TypeError otherwise.

    threshold: float

    Returns
    -------
    binarised_img: numpy.ndarray
        Mask volume
    """
    img = check_img(image)
    return img.get_data() > threshold


def union_mask(filelist):
    """
    Creates a binarised mask with the union of the files in filelist.

    Parameters
    ----------
    filelist: list of img-like object or boyle.nifti.NeuroImage or str
        List of paths to the volume files containing the ROIs.
        Can either be:
        - a file path to a Nifti image
        - any object with get_data() and get_affine() methods, e.g., nibabel.Nifti1Image.
        If niimg is a string, consider it as a path to Nifti image and
        call nibabel.load on it. If it is an object, check if get_data()
        and get_affine() methods are present, raise TypeError otherwise.

    Returns
    -------
    ndarray of bools
        Mask volume

    Raises
    ------
    ValueError
    """
    firstimg = check_img(filelist[0])
    mask     = np.zeros_like(firstimg.get_data())

    # create space for all features and read from subjects
    try:
        for volf in filelist:
            roiimg = check_img(volf)
            check_img_compatibility(firstimg, roiimg)
            mask  += get_img_data(roiimg)
    except Exception as exc:
        raise ValueError('Error joining mask {} and {}.'.format(repr_imgs(firstimg), repr_imgs(volf))) from exc
    else:
        return as_ndarray(mask > 0, dtype=bool)


def apply_mask(image, mask_img):
    """Read a Nifti file nii_file and a mask Nifti file.
    Returns the voxels in nii_file that are within the mask, the mask indices
    and the mask shape.

    Parameters
    ----------
    image: img-like object or boyle.nifti.NeuroImage or str
        Can either be:
        - a file path to a Nifti image
        - any object with get_data() and get_affine() methods, e.g., nibabel.Nifti1Image.
        If niimg is a string, consider it as a path to Nifti image and
        call nibabel.load on it. If it is an object, check if get_data()
        and get_affine() methods are present, raise TypeError otherwise.

    mask_img: img-like object or boyle.nifti.NeuroImage or str
        3D mask array: True where a voxel should be used.
        See img description.

    Returns
    -------
    vol[mask_indices], mask_indices

    Note
    ----
    nii_file and mask_file must have the same shape.

    Raises
    ------
    NiftiFilesNotCompatible, ValueError
    """
    img  = check_img(image)
    mask = check_img(mask_img)
    check_img_compatibility(img, mask)

    vol          = img.get_data()
    mask_data, _ = load_mask_data(mask)

    return vol[mask_data], mask_data


def apply_mask_4d(image, mask_img):  # , smooth_mm=None, remove_nans=True):
    """Read a Nifti file nii_file and a mask Nifti file.
    Extract the signals in nii_file that are within the mask, the mask indices
    and the mask shape.

    Parameters
    ----------
    image: img-like object or boyle.nifti.NeuroImage or str
        Can either be:
        - a file path to a Nifti image
        - any object with get_data() and get_affine() methods, e.g., nibabel.Nifti1Image.
        If niimg is a string, consider it as a path to Nifti image and
        call nibabel.load on it. If it is an object, check if get_data()
        and get_affine() methods are present, raise TypeError otherwise.

    mask_img: img-like object or boyle.nifti.NeuroImage or str
        3D mask array: True where a voxel should be used.
        See img description.

    smooth_mm: float #TBD
        (optional) The size in mm of the FWHM Gaussian kernel to smooth the signal.
        If True, remove_nans is True.

    remove_nans: bool #TBD
        If remove_nans is True (default), the non-finite values (NaNs and
        infs) found in the images will be replaced by zeros.

    Returns
    -------
    session_series, mask_data

    session_series: numpy.ndarray
        2D array of series with shape (voxel number, image number)

    Note
    ----
    nii_file and mask_file must have the same shape.

    Raises
    ------
    FileNotFound, NiftiFilesNotCompatible
    """
    img  = check_img(image)
    mask = check_img(mask_img)
    check_img_compatibility(img, mask, only_check_3d=True)

    vol = get_data(img)
    series, mask_data = _apply_mask_to_4d_data(vol, mask)
    return series, mask_data


def _apply_mask_to_4d_data(vol_data, mask_img):
    """
    Parameters
    ----------
    vol_data:
    mask_img:

    Returns
    -------
    masked_data, mask_indices

    masked_data: numpy.ndarray
        2D array of series with shape (image number, voxel number)

    Note
    ----
    vol_data and mask_file must have the same shape.
    """
    mask_data = load_mask_data(mask_img)

    return vol_data[mask_data], mask_data


def vector_to_volume(arr, mask, order='C'):
    """Transform a given vector to a volume. This is a reshape function for
    3D flattened and maybe masked vectors.

    Parameters
    ----------
    arr: np.array
        1-Dimensional array

    mask: numpy.ndarray
        Mask image. Must have 3 dimensions, bool dtype.

    Returns
    -------
    np.ndarray
    """
    if mask.dtype != np.bool:
        raise ValueError("mask must be a boolean array")

    if arr.ndim != 1:
        raise ValueError("vector must be a 1-dimensional array")

    if arr.ndim == 2 and any(v == 1 for v in arr.shape):
        log.debug('Got an array of shape {}, flattening for my purposes.'.format(arr.shape))
        arr = arr.flatten()

    volume = np.zeros(mask.shape[:3], dtype=arr.dtype, order=order)
    volume[mask] = arr
    return volume


def matrix_to_4dvolume(arr, mask, order='C'):
    """Transform a given vector to a volume. This is a reshape function for
    4D flattened masked matrices where the second dimension of the matrix
    corresponds to the original 4th dimension.

    Parameters
    ----------
    arr: numpy.array
        2D numpy.array

    mask: numpy.ndarray
        Mask image. Must have 3 dimensions, bool dtype.

    dtype: return type
        If None, will get the type from vector

    Returns
    -------
    data: numpy.ndarray
        Unmasked data.
        Shape: (mask.shape[0], mask.shape[1], mask.shape[2], X.shape[1])
    """
    if mask.dtype != np.bool:
        raise ValueError("mask must be a boolean array")

    if arr.ndim != 2:
        raise ValueError("X must be a 2-dimensional array")

    if mask.sum() != arr.shape[0]:
        # raise an error if the shape of arr is not what expected
        raise ValueError('Expected arr of shape ({}, samples). Got {}.'.format(mask.sum(), arr.shape))

    data = np.zeros(mask.shape + (arr.shape[1],), dtype=arr.dtype,
                    order=order)
    data[mask, :] = arr
    return data

    #
    # if matrix.ndim != 2:
    #     raise ValueError('A 2D matrix was expected but got a matrix with {} dimensios.'.format(matrix.ndim))
    #
    # if dtype is None:
    #     dtype = matrix.dtype
    #
    # vols_num = matrix.shape[1]
    # volume = np.zeros(mask_shape + (vols_num, ), dtype=dtype)
    # try:
    #     for i in range(vols_num):
    #         volume[mask_indices[0], mask_indices[1], mask_indices[2], i] = matrix[:, i]
    # except Exception:
    #     raise#ValueError('Error on transforming matrix to volume.')
    # else:
    #     return volume


def niftilist_mask_to_array(img_filelist, mask_file=None, outdtype=None):
    """From the list of absolute paths to nifti files, creates a Numpy array
    with the masked data.

    Parameters
    ----------
    img_filelist: list of str
        List of absolute file paths to nifti files. All nifti files must have
        the same shape.

    mask_file: str
        Path to a Nifti mask file.
        Should be the same shape as the files in nii_filelist.

    outdtype: dtype
        Type of the elements of the array, if not set will obtain the dtype from
        the first nifti file.

    Returns
    -------
    outmat:
        Numpy array with shape N x prod(vol.shape) containing the N files as flat vectors.

    mask_indices:
        Tuple with the 3D spatial indices of the masking voxels, for reshaping
        with vol_shape and remapping.

    vol_shape:
        Tuple with shape of the volumes, for reshaping.

    """
    img = check_img(img_filelist[0])
    if not outdtype:
        outdtype = img.dtype

    mask_data, _ = load_mask_data(mask_file)
    indices      = np.where      (mask_data)

    mask = check_img(mask_file)

    outmat = np.zeros((len(img_filelist), np.count_nonzero(mask_data)),
                      dtype=outdtype)

    for i, img_item in enumerate(img_filelist):
        img = check_img(img_item)
        if not are_compatible_imgs(img, mask):
            raise NiftiFilesNotCompatible(repr_imgs(img), repr_imgs(mask_file))

        vol = get_img_data(img)
        outmat[i, :] = vol[indices]

    return outmat, mask_data
