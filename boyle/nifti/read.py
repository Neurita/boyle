# coding=utf-8
"""
Nifti file access utilities.
"""
#------------------------------------------------------------------------------

#Author: Alexandre Manhaes Savio <alexsavio@gmail.com>
#Grupo de Inteligencia Computational <www.ehu.es/ccwintco>
#Universidad del Pais Vasco UPV/EHU
#
#2013, Alexandre Manhaes Savio
#Use this at your own risk!
#------------------------------------------------------------------------------

import os
import copy
import operator
import numpy   as np
import nibabel as nib
from   distutils.version import LooseVersion

from .check import check_img, repr_imgs, get_data
from ..exceptions import FileNotFound
from ..utils import as_ndarray
from ..utils.compat import _basestring


import warnings


def read_img(img_file):
    """Return a representation of the image, either a nibabel.Nifti1Image or the same object as img_file.
    See boyle.nifti.check_img.

    Parameters
    ----------
    img: img-like object or str
        Can either be:
        - a file path to a Nifti image
        - any object with get_data() and get_affine() methods, e.g., nibabel.Nifti1Image.
        If niimg is a string, consider it as a path to Nifti image and
        call nibabel.load on it. If it is an object, check if get_data()
        and get_affine() methods are present, raise TypeError otherwise.

    Returns
    -------
    img
    """
    return check_img(img_file)


def get_nii_info(img_file):
    """See get_img_info"""
    warnings.warn("get_nii_info will be removed soon. Please use get_img_info or NeuroImage instead.",
                  DeprecationWarning)
    return get_img_info(img_file)


def get_nii_data(nii_file):
    """See get_img_data"""
    warnings.warn("get_nii_data will be removed soon. Please use get_img_data or NeuroImage instead.",
                  DeprecationWarning)
    return get_img_data(nii_file)


def get_img_info(image):
    """Return the header and affine matrix from a Nifti file.

    Parameters
    ----------
    image: img-like object or str
        Can either be:
        - a file path to a Nifti image
        - any object with get_data() and get_affine() methods, e.g., nibabel.Nifti1Image.
        If niimg is a string, consider it as a path to Nifti image and
        call nibabel.load on it. If it is an object, check if get_data()
        and get_affine() methods are present, raise TypeError otherwise.

    Returns
    -------
    hdr, aff
    """
    try:
        img = check_img(image)
    except Exception as exc:
        raise Exception('Error reading file {0}.'.format(repr_imgs(image))) from exc
    else:
        return img.get_header(), img.get_affine()


def get_img_data(image, copy=True):
    """Return the voxel matrix of the Nifti file.
    If safe_mode will make a copy of the img before returning the data, so the input image is not modified.

    Parameters
    ----------
    image: img-like object or str
        Can either be:
        - a file path to a Nifti image
        - any object with get_data() and get_affine() methods, e.g., nibabel.Nifti1Image.
        If niimg is a string, consider it as a path to Nifti image and
        call nibabel.load on it. If it is an object, check if get_data()
        and get_affine() methods are present, raise TypeError otherwise.

    copy: bool
    If safe_mode will make a copy of the img before returning the data, so the input image is not modified.

    Returns
    -------
    array_like
    """
    try:
        img = check_img(image)
        if copy:
            return get_data(img)
        else:
            return img.get_data()
    except Exception as exc:
        raise Exception('Error when reading file {0}.'.format(repr_imgs(image))) from exc


def load_nipy_img(nii_file):
    """Read a Nifti file and return as nipy.Image

    Parameters
    ----------
    param nii_file: str
        Nifti file path

    Returns
    -------
    nipy.Image
    """
    # delayed import because could not install nipy on Python 3 on OSX
    import nipy

    if not os.path.exists(nii_file):
        raise FileNotFound(nii_file)

    try:
        return nipy.load_image(nii_file)
    except Exception as exc:
        raise Exception('Reading file {0}.'.format(repr_imgs(nii_file))) from exc


def niftilist_to_array(img_filelist, outdtype=None):
    """
    From the list of absolute paths to nifti files, creates a Numpy array
    with the data.

    Parameters
    ----------
    img_filelist:  list of str
        List of absolute file paths to nifti files. All nifti files must have
        the same shape.

    outdtype: dtype
        Type of the elements of the array, if not set will obtain the dtype from
        the first nifti file.

    Returns
    -------
    outmat: Numpy array with shape N x prod(vol.shape)
            containing the N files as flat vectors.

    vol_shape: Tuple with shape of the volumes, for reshaping.

    """
    try:
        first_img = img_filelist[0]
        vol       = get_img_data(first_img)
    except IndexError as ie:
        raise Exception('Error getting the first item of img_filelis: {}'.format(repr_imgs(img_filelist[0]))) from ie

    if not outdtype:
        outdtype = vol.dtype

    outmat = np.zeros((len(img_filelist), np.prod(vol.shape)), dtype=outdtype)

    try:
        for i, img_file in enumerate(img_filelist):
            vol = get_img_data(img_file)
            outmat[i, :] = vol.flatten()
    except Exception as exc:
        raise Exception('Error on reading file {0}.'.format(img_file)) from exc

    return outmat, vol.shape


def _crop_img_to(image, slices, copy=True):
    """Crops image to a smaller size

    Crop img to size indicated by slices and modify the affine accordingly.

    Parameters
    ----------
    image: img-like object or str
        Can either be:
        - a file path to a Nifti image
        - any object with get_data() and get_affine() methods, e.g., nibabel.Nifti1Image.
        If niimg is a string, consider it as a path to Nifti image and
        call nibabel.load on it. If it is an object, check if get_data()
        and get_affine() methods are present, raise TypeError otherwise.

        Image to be cropped.

    slices: list of slices
        Defines the range of the crop.
        E.g. [slice(20, 200), slice(40, 150), slice(0, 100)]
        defines a 3D cube

        If slices has less entries than image has dimensions,
        the slices will be applied to the first len(slices) dimensions.

    copy: boolean
        Specifies whether cropped data is to be copied or not.
        Default: True

    Returns
    -------
    cropped_img: img-like object
        Cropped version of the input image
    """

    img    = check_img(image)
    data   = img.get_data()
    affine = img.get_affine()

    cropped_data = data[slices]
    if copy:
        cropped_data   = cropped_data.copy()

    linear_part        = affine[:3, :3]
    old_origin         = affine[:3,  3]
    new_origin_voxel   = np.array([s.start for s in slices])
    new_origin         = old_origin + linear_part.dot(new_origin_voxel)

    new_affine         = np.eye(4)
    new_affine[:3, :3] = linear_part
    new_affine[:3,  3] = new_origin

    new_img = nib.Nifti1Image(cropped_data, new_affine)

    return new_img


def crop_img(image, rtol=1e-8, copy=True):
    """Crops img as much as possible

    Will crop img, removing as many zero entries as possible
    without touching non-zero entries. Will leave one voxel of
    zero padding around the obtained non-zero area in order to
    avoid sampling issues later on.

    Parameters
    ----------
    image: img-like object or str
        Can either be:
        - a file path to a Nifti image
        - any object with get_data() and get_affine() methods, e.g., nibabel.Nifti1Image.
        If niimg is a string, consider it as a path to Nifti image and
        call nibabel.load on it. If it is an object, check if get_data()
        and get_affine() methods are present, raise TypeError otherwise.

        Image to be cropped.

    rtol: float
        relative tolerance (with respect to maximal absolute
        value of the image), under which values are considered
        negligeable and thus croppable.

    copy: boolean
        Specifies whether cropped data is copied or not.

    Returns
    -------
    cropped_img: image
        Cropped version of the input image
    """

    img              = check_img(image)
    data             = img.get_data()
    infinity_norm    = max(-data.min(), data.max())
    passes_threshold = np.logical_or(data < -rtol * infinity_norm,
                                     data >  rtol * infinity_norm)

    if data.ndim == 4:
        passes_threshold = np.any(passes_threshold, axis=-1)

    coords = np.array(np.where(passes_threshold))
    start  = coords.min(axis=1)
    end    = coords.max(axis=1) + 1

    # pad with one voxel to avoid resampling problems
    start = np.maximum(start - 1, 0)
    end   = np.minimum(end   + 1, data.shape[:3])

    slices = [slice(s, e) for s, e in zip(start, end)]

    return _crop_img_to(img, slices, copy=copy)


def new_img_like(ref_niimg, data, affine=None, copy_header=False):
    """Create a new image of the same class as the reference image

    Parameters
    ----------
    ref_niimg: image
        Reference image. The new image will be of the same type.

    data: numpy array
        Data to be stored in the image

    affine: 4x4 numpy array, optional
        Transformation matrix

    copy_header: boolean, optional
        Indicated if the header of the reference image should be used to
        create the new image

    Returns
    -------
    new_img: image
        A loaded image with the same type (and header) as the reference image.
    """
    # Hand-written loading code to avoid too much memory consumption
    if not (hasattr(ref_niimg, 'get_data')
              and hasattr(ref_niimg,'get_affine')):
        if isinstance(ref_niimg, _basestring):
            ref_niimg = nib.load(ref_niimg)
        elif operator.isSequenceType(ref_niimg):
            ref_niimg = nib.load(ref_niimg[0])
        else:
            raise TypeError(('The reference image should be a niimg, %r '
                            'was passed') % ref_niimg )

    if affine is None:
        affine = ref_niimg.get_affine()
    if data.dtype == bool:
        default_dtype = np.int8
        if (LooseVersion(nib.__version__) >= LooseVersion('1.2.0') and
                isinstance(ref_niimg, nib.freesurfer.mghformat.MGHImage)):
            default_dtype = np.uint8
        data = as_ndarray(data, dtype=default_dtype)
    header = None
    if copy_header:
        header = copy.copy(ref_niimg.get_header())
        header['scl_slope'] = 0.
        header['scl_inter'] = 0.
        header['glmax'] = 0.
        header['cal_max'] = np.max(data) if data.size > 0 else 0.
        header['cal_max'] = np.min(data) if data.size > 0 else 0.
    return ref_niimg.__class__(data, affine, header=header)
