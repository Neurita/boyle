
import logging
import numpy            as np
import nibabel          as nib
import scipy.ndimage    as ndimage
from   six              import string_types

from   .check           import check_img

from   nilearn._utils       import check_niimg
from   nilearn.image.image  import new_img_like, _fast_smooth_array


log = logging.getLogger(__name__)

# def smooth_volume(nifti_file, smoothmm):
#     """
#
#     @param nifti_file: string
#     @param smoothmm: int
#     @return:
#     """
# from nipy.algorithms.kernel_smooth import LinearFilter
# from nipy import load_image
#     try:
#         img = load_image(nifti_file)
#     except Exception:
#         log.exception('Error reading file {0}.'.format(nifti_file))
#         raise
#
#     if smoothmm <= 0:
#         return img
#
#     filter = LinearFilter(img.coordmap, img.shape)
#     return filter.smooth(img)
#

def fwhm2sigma(fwhm):
    """Convert a FWHM value to sigma in a Gaussian kernel.

    Parameters
    ----------
    fwhm: float or numpy.array
       fwhm value or values

    Returns
    -------
    fwhm: float or numpy.array
       sigma values
    """
    fwhm = np.asarray(fwhm)
    return fwhm / np.sqrt(8 * np.log(2))


def sigma2fwhm(sigma):
    """Convert a sigma in a Gaussian kernel to a FWHM value.

    Parameters
    ----------
    sigma: float or numpy.array
       sigma value or values

    Returns
    -------
    fwhm: float or numpy.array
       fwhm values corresponding to `sigma` values
    """
    sigma = np.asarray(sigma)
    return np.sqrt(8 * np.log(2)) * sigma


def smooth_volume(image, smoothmm):
    """See smooth_img."""
    return smooth_imgs(image, smoothmm)


def _smooth_data_array(arr, affine, fwhm, copy=True):
    """Smooth images with a a Gaussian filter.

    Apply a Gaussian filter along the three first dimensions of arr.

    Parameters
    ----------
    arr: numpy.ndarray
        3D or 4D array, with image number as last dimension.

    affine: numpy.ndarray
        Image affine transformation matrix for image.

    fwhm: scalar, numpy.ndarray
        Smoothing kernel size, as Full-Width at Half Maximum (FWHM) in millimeters.
        If a scalar is given, kernel width is identical on all three directions.
        A numpy.ndarray must have 3 elements, giving the FWHM along each axis.

    copy: bool
        if True, will make a copy of the input array. Otherwise will directly smooth the input array.

    Returns
    -------
    smooth_arr: numpy.ndarray
    """

    if arr.dtype.kind == 'i':
        if arr.dtype == np.int64:
            arr = arr.astype(np.float64)
        else:
            arr = arr.astype(np.float32)
    if copy:
        arr = arr.copy()

    # Zeroe possible NaNs and Inf in the image.
    arr[np.logical_not(np.isfinite(arr))] = 0

    try:
        # Keep the 3D part of the affine.
        affine = affine[:3, :3]

        # Convert from FWHM in mm to a sigma.
        fwhm_sigma_ratio = np.sqrt(8 * np.log(2))
        vox_size         = np.sqrt(np.sum(affine ** 2, axis=0))
        sigma            = fwhm / (fwhm_sigma_ratio * vox_size)
        for n, s in enumerate(sigma):
            ndimage.gaussian_filter1d(arr, s, output=arr, axis=n)
    except:
        raise ValueError('Error smoothing the array.')
    else:
        return arr


def smooth_imgs(images, fwhm):
    """Smooth images using a Gaussian filter.

    Apply a Gaussian filter along the three first dimensions of each image in images.
    In all cases, non-finite values in input are zeroed.

    Parameters
    ----------
    imgs: str or img-like object or iterable of img-like objects
        See boyle.nifti.read.read_img
        Image(s) to smooth.

    fwhm: scalar or numpy.ndarray
        Smoothing kernel size, as Full-Width at Half Maximum (FWHM) in millimeters.
        If a scalar is given, kernel width is identical on all three directions.
        A numpy.ndarray must have 3 elements, giving the FWHM along each axis.

    Returns
    -------
    smooth_imgs: nibabel.Nifti1Image or list of.
        Smooth input image/s.
    """
    if fwhm <= 0:
        return images

    if not isinstance(images, string_types) and hasattr(images, '__iter__'):
        only_one = False
    else:
        only_one = True
        images = [images]

    result = []
    for img in images:
        img    = check_img(img)
        affine = img.get_affine()
        smooth = _smooth_data_array(img.get_data(), affine, fwhm=fwhm, copy=True)
        result.append(nib.Nifti1Image(smooth, affine))

    if only_one:
        return result[0]
    else:
        return result


def _smooth_array(arr, affine, fwhm=None, ensure_finite=True, copy=True, **kwargs):
    """Smooth images by applying a Gaussian filter.
    Apply a Gaussian filter along the three first dimensions of arr.

    This is copied and slightly modified from nilearn:
    https://github.com/nilearn/nilearn/blob/master/nilearn/image/image.py
    Added the **kwargs argument.

    Parameters
    ==========
    arr: numpy.ndarray
        4D array, with image number as last dimension. 3D arrays are also
        accepted.
    affine: numpy.ndarray
        (4, 4) matrix, giving affine transformation for image. (3, 3) matrices
        are also accepted (only these coefficients are used).
        If fwhm='fast', the affine is not used and can be None
    fwhm: scalar, numpy.ndarray, 'fast' or None
        Smoothing strength, as a full-width at half maximum, in millimeters.
        If a scalar is given, width is identical on all three directions.
        A numpy.ndarray must have 3 elements, giving the FWHM along each axis.
        If fwhm == 'fast', a fast smoothing will be performed with
        a filter [0.2, 1, 0.2] in each direction and a normalisation
        to preserve the local average value.
        If fwhm is None, no filtering is performed (useful when just removal
        of non-finite values is needed).
    ensure_finite: bool
        if True, replace every non-finite values (like NaNs) by zero before
        filtering.
    copy: bool
        if True, input array is not modified. False by default: the filtering
        is performed in-place.
    kwargs: keyword-arguments
        Arguments for the ndimage.gaussian_filter1d function.

    Returns
    =======
    filtered_arr: numpy.ndarray
        arr, filtered.
    Notes
    =====
    This function is most efficient with arr in C order.
    """

    if arr.dtype.kind == 'i':
        if arr.dtype == np.int64:
            arr = arr.astype(np.float64)
        else:
            # We don't need crazy precision
            arr = arr.astype(np.float32)
    if copy:
        arr = arr.copy()

    if ensure_finite:
        # SPM tends to put NaNs in the data outside the brain
        arr[np.logical_not(np.isfinite(arr))] = 0

    if fwhm == 'fast':
        arr = _fast_smooth_array(arr)
    elif fwhm is not None:
        # Keep only the scale part.
        affine = affine[:3, :3]

        # Convert from a FWHM to a sigma:
        fwhm_over_sigma_ratio = np.sqrt(8 * np.log(2))
        vox_size = np.sqrt(np.sum(affine ** 2, axis=0))
        sigma = fwhm / (fwhm_over_sigma_ratio * vox_size)
        for n, s in enumerate(sigma):
            ndimage.gaussian_filter1d(arr, s, output=arr, axis=n, **kwargs)

    return arr


def smooth_img(imgs, fwhm, **kwargs):
    """Smooth images by applying a Gaussian filter.
    Apply a Gaussian filter along the three first dimensions of arr.
    In all cases, non-finite values in input image are replaced by zeros.

    This is copied and slightly modified from nilearn:
    https://github.com/nilearn/nilearn/blob/master/nilearn/image/image.py
    Added the **kwargs argument.

    Parameters
    ==========
    imgs: Niimg-like object or iterable of Niimg-like objects
        See http://nilearn.github.io/manipulating_images/manipulating_images.html#niimg.
        Image(s) to smooth.
    fwhm: scalar, numpy.ndarray, 'fast' or None
        Smoothing strength, as a Full-Width at Half Maximum, in millimeters.
        If a scalar is given, width is identical on all three directions.
        A numpy.ndarray must have 3 elements, giving the FWHM along each axis.
        If fwhm == 'fast', a fast smoothing will be performed with
        a filter [0.2, 1, 0.2] in each direction and a normalisation
        to preserve the scale.
        If fwhm is None, no filtering is performed (useful when just removal
        of non-finite values is needed)
    Returns
    =======
    filtered_img: nibabel.Nifti1Image or list of.
        Input image, filtered. If imgs is an iterable, then filtered_img is a
        list.
    """

    # Use hasattr() instead of isinstance to workaround a Python 2.6/2.7 bug
    # See http://bugs.python.org/issue7624
    if hasattr(imgs, "__iter__") \
       and not isinstance(imgs, string_types):
        single_img = False
    else:
        single_img = True
        imgs = [imgs]

    ret = []
    for img in imgs:
        img = check_niimg(img)
        affine = img.get_affine()
        filtered = _smooth_array(img.get_data(), affine, fwhm=fwhm,
                                 ensure_finite=True, copy=True, **kwargs)
        ret.append(new_img_like(img, filtered, affine, copy_header=True))

    if single_img:
        return ret[0]
    else:
        return ret
