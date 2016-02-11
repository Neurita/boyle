
import logging
import numpy            as np
import nibabel          as nib
import scipy.ndimage    as ndimg
from   six              import string_types

from   .check           import check_img

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
            ndimg.gaussian_filter1d(arr, s, output=arr, axis=n)
    except:
        raise ValueError('')
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
