# coding=utf-8
"""
Nifti file consistency checking utilities
"""
#------------------------------------------------------------------------------

#Author: Alexandre Manhaes Savio <alexsavio@gmail.com>
#Grupo de Inteligencia Computational <www.ehu.es/ccwintco>
#Universidad del Pais Vasco UPV/EHU
#
#2013, Alexandre Manhaes Savio
#Use this at your own risk!
#------------------------------------------------------------------------------


import gc
import copy
import logging
import collections

import os.path      as     op
import numpy        as     np
import nibabel      as     nib
from   six          import string_types

from   ..exceptions import FileNotFound, NiftiFilesNotCompatible


log = logging.getLogger(__name__)


def is_img(obj):
    """ Check for get_data and get_affine method in an object

    Parameters
    ----------
    obj: any object
        Tested object

    Returns
    -------
    is_img: boolean
        True if get_data and get_affine methods are present and callable,
        False otherwise.
    """
    try:
        get_data   = getattr(obj, 'get_data')
        get_affine = getattr(obj, 'get_affine')

        return isinstance(get_data,   collections.Callable) and \
               isinstance(get_affine, collections.Callable)
    except AttributeError:
        return False


def get_data(img):
    """Get the data in the image without having a side effect on the Nifti1Image object

    Parameters
    ----------
    img: Nifti1Image

    Returns
    -------
    np.ndarray
    """
    if hasattr(img, '_data_cache') and img._data_cache is None:
        # Copy locally the nifti_image to avoid the side effect of data
        # loading
        img = copy.deepcopy(img)
    # force garbage collector
    gc.collect()
    return img.get_data()


def get_shape(img):
    """Return the shape of img.

    Paramerers
    -----------
    img:

    Returns
    -------
    shape: tuple
    """
    if hasattr(img, 'shape'):
        shape = img.shape
    else:
        shape = img.get_data().shape
    return shape


def is_valid_coordinate(img, i, j, k):
    """Return True if the given (i, j, k) voxel grid coordinate values are within the img boundaries.

    Parameters
    ----------
    @param img:
    @param i:
    @param j:
    @param k:

    Returns
    -------
    bool
    """
    imgx, imgy, imgz = get_shape(img)
    return (i >= 0 and i < imgx) and \
           (j >= 0 and j < imgy) and \
           (k >= 0 and k < imgz)


def are_compatible_imgs(one_img, another_img):
    """Return true if one_img and another_img have the same shape.
    False otherwise.
    If both are nibabel.Nifti1Image will also check for affine matrices.

    Parameters
    ----------
    one_img: nibabel.Nifti1Image or np.ndarray

    another_img: nibabel.Nifti1Image  or np.ndarray

    Returns
    -------
    bool
    """
    try:
        check_img_compatibility(one_img, another_img)
    except :
        return False
    else:
        return True


def check_img_compatibility(one_img, another_img, only_check_3d=False):
    """Return true if one_img and another_img have the same shape.
    False otherwise.
    If both are nibabel.Nifti1Image will also check for affine matrices.

    Parameters
    ----------
    one_img: nibabel.Nifti1Image or np.ndarray

    another_img: nibabel.Nifti1Image  or np.ndarray

    only_check_3d: bool
        If True will check only the 3D part of the affine matrices when they have more dimensions.

    Raises
    ------
    NiftiFilesNotCompatible
    """
    nd_to_check = None
    if only_check_3d:
        nd_to_check = 3

    if hasattr(one_img, 'shape') and hasattr(another_img, 'shape'):
        if not have_same_shape(one_img, another_img, nd_to_check=nd_to_check):
            msg = 'Shape of the first image: \n{}\n is different from second one: \n{}'.format(one_img.shape,
                                                                                               another_img.shape)
            raise NiftiFilesNotCompatible(repr_imgs(one_img), repr_imgs(another_img), message=msg)

    if hasattr(one_img, 'get_affine') and hasattr(another_img, 'get_affine'):
        if not have_same_affine(one_img, another_img, only_check_3d=only_check_3d):
            msg = 'Affine matrix of the first image: \n{}\n is different ' \
                  'from second one:\n{}'.format(one_img.get_affine(), another_img.get_affine())
            raise NiftiFilesNotCompatible(repr_imgs(one_img), repr_imgs(another_img), message=msg)


def have_same_affine(one_img, another_img, only_check_3d=False):
    """Return True if the affine matrix of one_img is close to the affine matrix of another_img.
    False otherwise.

    Parameters
    ----------
    one_img: nibabel.Nifti1Image

    another_img: nibabel.Nifti1Image

    only_check_3d: bool
        If True will extract only the 3D part of the affine matrices when they have more dimensions.

    Returns
    -------
    bool

    Raises
    ------
    ValueError

    """
    img1 = check_img(one_img)
    img2 = check_img(another_img)

    ndim1 = len(img1.shape)
    ndim2 = len(img2.shape)

    if ndim1 < 3:
        raise ValueError('Image {} has only {} dimensions, at least 3 dimensions is expected.'.format(repr_imgs(img1), ndim1))

    if ndim2 < 3:
        raise ValueError('Image {} has only {} dimensions, at least 3 dimensions is expected.'.format(repr_imgs(img2), ndim1))

    affine1 = img1.get_affine()
    affine2 = img2.get_affine()
    if only_check_3d:
        affine1 = affine1[:3, :3]
        affine2 = affine2[:3, :3]

    try:
        return np.allclose(affine1, affine2)
    except ValueError:
        return False
    except:
        raise


def _make_it_3d(img):
    """Enforce that img is a 3D img-like object, if it is not, raise a TypeError.
    i.e., remove dimensions of size 1.

    Parameters
    ----------
    img: img-like object

    Returns
    -------
    3D img-like object
    """
    shape = get_shape(img)
    if len(shape) == 3:
        return img

    elif (len(shape) == 4 and shape[3] == 1):
        # "squeeze" the image.
        try:
            data   = get_data(img)
            affine = img.get_affine()
            img    = nib.Nifti1Image(data[:, :, :, 0], affine)
        except Exception as exc:
            raise Exception("Error making image '{}' a 3D volume file.".format(img)) from exc
        else:
            return img
    else:
        raise TypeError("A 3D image is expected, but an image with a shape of {} was given.".format(shape))


def check_img(image, make_it_3d=False):
    """Check that image is a proper img. Turn filenames into objects.

    Parameters
    ----------
    image: img-like object or str
        Can either be:
        - a file path to a Nifti image
        - any object with get_data() and get_affine() methods, e.g., nibabel.Nifti1Image.
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
        if not op.exists(image):
            raise FileNotFound(image)

        try:
            img = nib.load(image)
            if make_it_3d:
                img = _make_it_3d(img)
        except Exception as exc:
            raise Exception('Error loading image file {}.'.format(image)) from exc
        else:
            return img

    elif isinstance(image, nib.Nifti1Image) or is_img(image):
        return image

    else:
        raise TypeError('Data given cannot be converted to a nifti'
                        ' image: this object -"{}"- does not have'
                        ' get_data or get_affine methods'.format(type(image)))


def repr_imgs(imgs):
    """Printing of img or imgs"""
    if isinstance(imgs, string_types):
        return imgs

    if isinstance(imgs, collections.Iterable):
        return '[{}]'.format(', '.join(repr_imgs(img) for img in imgs))

    # try get_filename
    try:
        filename = imgs.get_filename()
        if filename is not None:
            img_str = "{}('{}')".format(imgs.__class__.__name__, filename)
        else:
            img_str = "{}(shape={}, affine={})".format(imgs.__class__.__name__,
                                                       repr(get_shape(imgs)),
                                                       repr(imgs.get_affine()))
    except Exception as exc:
        log.error('Error reading attributes from img.get_filename()')
        return repr(imgs)
    else:
        return img_str


def repr_img(img):
    """Printing of img or imgs. See repr_imgs."""
    return repr_imgs(img)


def have_same_shape(array1, array2, nd_to_check=None):
    """
    Returns true if array1 and array2 have the same shapes, false
    otherwise.

    Parameters
    ----------
    array1: numpy.ndarray

    array2: numpy.ndarray

    nd_to_check: int
        Number of the dimensions to check, i.e., if == 3 then will check only the 3 first numbers of array.shape.
    Returns
    -------
    bool
    """
    shape1 = array1.shape
    shape2 = array2.shape
    if nd_to_check is not None:
        if len(shape1) < nd_to_check:
            msg = 'Number of dimensions to check {} is out of bounds for the shape of the first image: \n{}\n.'.format(shape1)
            raise ValueError(msg)
        elif len(shape2) < nd_to_check:
            msg = 'Number of dimensions to check {} is out of bounds for the shape of the second image: \n{}\n.'.format(shape2)
            raise ValueError(msg)

        shape1 = shape1[:nd_to_check]
        shape2 = shape2[:nd_to_check]

    return shape1 == shape2


def have_same_geometry(fname1, fname2):
    """
    @param fname1: string
    File path of an image

    @param fname2: string
    File path of an image

    @return: bool
    True if both have the same geometry
    """
    img1shape = nib.load(fname1).get_shape()
    img2shape = nib.load(fname2).get_shape()
    return have_same_shape(img1shape, img2shape)


def have_same_spatial_geometry(fname1, fname2):
    """
    @param fname1: string
    File path of an image

    @param fname2: string
    File path of an image

    @return: bool
    True if both have the same geometry
    """
    img1shape = nib.load(fname1).get_shape()
    img2shape = nib.load(fname2).get_shape()
    return img1shape[:3] == img2shape[:3]


def check_have_same_geometry(fname1, fname2):
    """
    @param fname1:
    @param fname2:
    """
    if not have_same_geometry(fname1, fname2):
        raise ArithmeticError('Different shapes:' + fname1 + ' vs. ' + fname2)


def check_have_same_spatial_geometry(fname1, fname2):
    """
    @param fname1:
    @param fname2:
    """
    if not have_same_spatial_geometry(fname1, fname2):
        raise ArithmeticError('Different shapes:' + fname1 + ' vs. ' + fname2)


def get_sampling_interval(func_img):
    """
    Extracts the supposed sampling interval (TR) from the nifti file header.

    @param func_img: a NiBabel SpatialImage

    @return: float
    The TR value from the image header
    """
    return func_img.get_header().get_zooms()[-1]
