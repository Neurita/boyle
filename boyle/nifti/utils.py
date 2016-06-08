# coding=utf-8
"""
Utilities to manage volume files
"""
#------------------------------------------------------------------------------
# Author: Alexandre Manhaes Savio <alexsavio@gmail.com>
# Nuklear Medizin Department
# Klinikum rechts der Isar der Technische Universitaet Muenchen, Deutschland
#
# 2015, Alexandre Manhaes Savio
# Use this at your own risk!
#------------------------------------------------------------------------------

from functools import wraps

import numpy as np
import nibabel as nib
from scipy.signal import detrend

from .read import read_img
from .check import check_img_compatibility, check_img, is_img
from .mask import vector_to_volume, apply_mask


def merge_images(images, axis='t'):
    """ Concatenate `images` in the direction determined in `axis`.

    Parameters
    ----------
    images: list of str or img-like object.
        See NeuroImage constructor docstring.

    axis: str
      't' : concatenate images in time
      'x' : concatenate images in the x direction
      'y' : concatenate images in the y direction
      'z' : concatenate images in the z direction

    Returns
    -------
    merged: img-like object
    """
    # check if images is not empty
    if not images:
        return None

    # the given axis name to axis idx
    axis_dim = {'x': 0,
                'y': 1,
                'z': 2,
                't': 3,
                }

    # check if the given axis name is valid
    if axis not in axis_dim:
        raise ValueError('Expected `axis` to be one of ({}), got {}.'.format(set(axis_dim.keys()), axis))

    # check if all images are compatible with each other
    img1 = images[0]
    for img in images:
        check_img_compatibility(img1, img)

    # read the data of all the given images
    # TODO: optimize memory consumption by merging one by one.
    image_data = []
    for img in images:
        image_data.append(check_img(img).get_data())

    # if the work_axis is bigger than the number of axis of the images,
    # create a new axis for the images
    work_axis = axis_dim[axis]
    ndim = image_data[0].ndim
    if ndim - 1 < work_axis:
        image_data = [np.expand_dims(img, axis=work_axis) for img in image_data]

    # concatenate and return
    return np.concatenate(image_data, axis=work_axis)


def nifti_out(f):
    """ Picks a function whose first argument is an `img`, processes its
    data and returns a numpy array. This decorator wraps this numpy array
    into a nibabel.Nifti1Image."""
    @wraps(f)
    def wrapped(*args, **kwargs):
        r = f(*args, **kwargs)

        img = read_img(args[0])
        return nib.Nifti1Image(r, affine=img.get_affine(), header=img.header)

    return wrapped


@nifti_out
def thr_img(img, thr=2., mode='+'):
    """ Use the given magic function name `func` to threshold with value `thr`
    the data of `img` and return a new nibabel.Nifti1Image.
    Parameters
    ----------
    img: img-like

    thr: float or int
        The threshold value.

    mode: str
        Choices: '+' for positive threshold,
                 '+-' for positive and negative threshold and
                 '-' for negative threshold.
    Returns
    -------
    thr_img: nibabel.Nifti1Image
        Thresholded image
    """

    vol  = read_img(img).get_data()

    if mode == '+':
        mask = vol > thr
    elif mode == '+-' or mode == '-+':
        mask = np.abs(vol) > thr
    elif mode == '-':
        mask = vol < -thr
    else:
        raise ValueError("Expected `mode` to be one of ('+', '+-', '-+', '-'), "
                         "got {}.".format(mode))

    return vol * mask


@nifti_out
def bin_img(img):
    """ Return an image with the positive voxels of the data of `img`."""
    return read_img(img).get_data() > 0


@nifti_out
def positive_img(img):
    """ Return an image with the positive voxels of the data of `img`."""
    bool_img = read_img(img).get_data() > 0
    return bool_img.astype(int)


@nifti_out
def negative_img(img):
    """ Return an image with the negative voxels of the data of `img`."""
    bool_img = read_img(img).get_data() < 0
    return bool_img.astype(int)


@nifti_out
def add_img(img1, img2):
    return img1.get_data() + img2.get_data()


@nifti_out
def max_img(img1, img2):
    return np.maximum(img1.get_data(), img2.get_data())


@nifti_out
def div_img(img1, div2):
    """ Pixelwise division or divide by a number """
    if is_img(div2):
        return img1.get_data()/div2.get_data()
    elif isinstance(div2, (float, int)):
        return img1.get_data()/div2
    else:
        raise NotImplementedError('Cannot divide {}({}) by '
                                  '{}({})'.format(type(img1),
                                                  img1,
                                                  type(div2),
                                                  div2))


@nifti_out
def apply_mask(img, mask):
    """Return the image with the given `mask` applied."""
    from .mask import apply_mask

    vol, _ = apply_mask(img, mask)
    return vector_to_volume(vol, read_img(mask).get_data().astype(bool))


@nifti_out
def abs_img(img):
    """ Return an image with the binarised version of the data of `img`."""
    bool_img = np.abs(read_img(img).get_data())
    return bool_img.astype(int)


@nifti_out
def icc_img_to_zscore(icc, center_image=False):
    """ Return a z-scored version of `icc`.
    This function is based on GIFT `icatb_convertImageToZScores` function.
    """
    vol = read_img(icc).get_data()

    v2 = vol[vol != 0]
    if center_image:
        v2 = detrend(v2, axis=0)

    vstd = np.linalg.norm(v2, ord=2) / np.sqrt(np.prod(v2.shape) - 1)

    eps = np.finfo(vstd.dtype).eps
    vol /= (eps + vstd)

    return vol


@nifti_out
def spatial_map(icc, thr, mode='+'):
    """ Return the thresholded z-scored `icc`. """
    return thr_img(icc_img_to_zscore(icc), thr=thr, mode=mode).get_data()


def filter_icc(icc, mask=None, thr=2, zscore=True, mode="+"):
    """ Threshold then mask an IC correlation map.
    Parameters
    ----------
    icc: img-like
        The 'raw' ICC map.

    mask: img-like
        If not None. Will apply this masks in the end of the process.

    thr: float
        The threshold value.

    zscore: bool
        If True will calculate the z-score of the ICC before thresholding.

    mode: str
        Choices: '+' for positive threshold,
                 '+-' for positive and negative threshold and
                 '-' for negative threshold.

    Returns
    -------
    icc_filt: nibabel.NiftiImage
        Thresholded and masked ICC.
    """
    if zscore:
        icc_filt = thr_img(icc_img_to_zscore(icc), thr=thr, mode=mode)
    else:
        icc_filt = thr_img(icc, thr=thr, mode=mode)

    if mask is not None:
        icc_filt = apply_mask(icc_filt, mask)

    return icc_filt
