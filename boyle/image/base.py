# coding=utf-8
"""
A class to manage neuroimage files. A wrapper around nibabel, nipy and the rest of boyle for own purposes.
"""
# ------------------------------------------------------------------------------
# Author: Alexandre Manhaes Savio <alexsavio@gmail.com>
# Klinikum rechts der Isar, TUM, Munich
#
# 2016, Alexandre Manhaes Savio
# Use this at your own risk!
# ------------------------------------------------------------------------------

import gc

import numpy                as np

from   ..nifti.read          import get_data
from   ..nifti.check         import check_img_compatibility, repr_imgs
from   ..nifti.mask          import load_mask, _apply_mask_to_4d_data, vector_to_volume, matrix_to_4dvolume
from   ..nifti.smooth        import _smooth_data_array
from   ..nifti.storage       import save_niigz

from .utils import _check_medimg


class ImageContainer(object):
    """ A image data container with a `img` and generic `header`.

    Parameters
    ----------
    image: img-like object or str
        Can either be:
        - a file path to a Nifti image or .mhd file
        - any object with get_data() and get_affine() methods, e.g., nibabel.Nifti1Image.
        If niimg is a string, consider it as a path to Nifti image and
        call nibabel.load on it. If it is an object, check if get_data()
        and get_affine() methods are present, raise TypeError otherwise.

    make_it_3d: boolean, optional
        If True, check if the image is a 3D image, if there is a 4th dimension with size 1, will remove it.
        In any other case will raise an error.

    cache_data: boolean, optional
        True if the data should be cached for faster access.

    Returns
    -------
    result: ImageContainer
       It is guaranteed that the returned object has get_data() method, and affine and header attributes.
    """
    def __init__(self, image, make_it_3d=False, cache_data=True):
        self.img      = _check_medimg(image, make_it_3d=make_it_3d)
        self._caching = 'fill' if cache_data else 'unchanged'

    def clear(self):
        self.clear_data()
        self.img  = None
        gc.collect()

    def clear_data(self):
        self.img.uncache()
        gc.collect()

    def has_data_loaded(self):
        return self.img.in_memory

    @property
    def ndim(self):
        return len(self.shape)

    @property
    def shape(self):
        if hasattr(self.img, 'shape'):
            return self.img.shape
        return None

    @property
    def dtype(self):
        return self.img.get_data_dtype()

    @property
    def affine(self):
        """Return the affine matrix from the image"""
        return self.img.affine

    @property
    def header(self):
        """Return the header from the image"""
        return self.img.header

    def get_filename(self):
        if hasattr(self.img, 'get_filename'):
            return self.img.get_filename()
        return None

    def pixdim(self):
        """ Return the voxel size in the header of the file. """
        return self.get_header().get_zooms()

    def get_data(self, safe_copy=False):
        """Get the data in the image.
         If save_copy is True, will perform a deep copy of the data and return it.

        Parameters
        ----------
        smoothed: (optional) bool
            If True and self._smooth_fwhm > 0 will smooth the data before masking.

        masked: (optional) bool
            If True and self.has_mask will return the masked data, the plain data otherwise.

        safe_copy: (optional) bool

        Returns
        -------
        np.ndarray
        """
        if safe_copy:
            data = get_data(self.img)
        else:
            data = self.img.get_data(caching=self._caching)

        return data

    def to_file(self, outpath):
        """Save this object instance in outpath.

        Parameters
        ----------
        outpath: str
            Output file path
        """
        save_niigz(outpath, self.img)

    def __repr__(self):
        return '<ImageContainer> ' + repr_imgs(self.img)

    def __str__(self):
        return self.__repr__()


class MedicalImage(ImageContainer):
    """MedImage is a class that wraps around different formats of medical images (Nifti, RAW, for now)
     offering compatibility with other external tools.

    This is a derivative class from ImageContainer that includes masking and smoothing helper functions as
    well as other utilities for medical image analysis.

    See ImageContainer for `__init__` reference.
    """
    def __init__(self, image, make_it_3d=False, cache_data=True):
        super(MedicalImage, self).__init__(image=image, make_it_3d=make_it_3d, cache_data=cache_data)
        self.mask     = None
        self.zeroe()

    def zeroe(self):
        self._smooth_fwhm    = 0
        self._is_data_masked = False
        self._is_data_smooth = False

    def clear(self):
        self.clear_data()
        self.zeroe()
        self.img  = None
        self.mask = None
        gc.collect()

    def clear_data(self):
        self.img.uncache()
        self.mask.uncache()
        gc.collect()

    @property
    def smooth_fwhm(self):
        return self._smooth_fwhm

    @smooth_fwhm.setter
    def smooth_fwhm(self, fwhm):
        """ Set a smoothing Gaussian kernel given its FWHM in mm.  """
        if fwhm != self._smooth_fwhm:
            self._is_data_smooth = False
        self._smooth_fwhm = fwhm

    def has_mask(self):
        return self.mask is not None

    def is_smoothed(self):
        return self._is_data_smooth

    def remove_smoothing(self):
        self._smooth_fwhm = 0
        self.img.uncache()

    def remove_masking(self):
        self.mask.uncache()
        self.mask = None

    def get_data(self, smoothed=True, masked=True, safe_copy=False):
        """Get the data in the image.
         If save_copy is True, will perform a deep copy of the data and return it.

        Parameters
        ----------
        smoothed: (optional) bool
            If True and self._smooth_fwhm > 0 will smooth the data before masking.

        masked: (optional) bool
            If True and self.has_mask will return the masked data, the plain data otherwise.

        safe_copy: (optional) bool

        Returns
        -------
        np.ndarray
        """
        if not safe_copy and smoothed == self._is_data_smooth and masked == self._is_data_masked:
            if self.has_data_loaded() and self._caching == 'fill':
                return self.get_data()

        if safe_copy:
            data = get_data(self.img)
        else:
            data = self.img.get_data(caching=self._caching)

        is_smoothed = False
        if smoothed and self._smooth_fwhm > 0:
            try:
                data = _smooth_data_array(data, self.get_affine(), self._smooth_fwhm, copy=False)
            except ValueError as ve:
                raise ValueError('Error smoothing image {} with a {}mm FWHM '
                                 'kernel.'.format(self.img, self._smooth_fwhm)) from ve
            else:
                is_smoothed = True

        is_data_masked = False
        if masked and self.has_mask():
            try:
                data = self.unmask(self._mask_data(data)[0])
            except:
                raise
            else:
                is_data_masked = True

        if not safe_copy:
            self._is_data_masked = is_data_masked
            self._is_data_smooth = is_smoothed

        return data

    def _check_for_mask(self):
        if not self.has_mask():
            raise AttributeError('Error looking for mask in {}, but if has no mask set up.'.format(self))

    def get_mask_indices(self):
        self._check_for_mask()

        return np.where(self.mask.get_data())

    def apply_mask(self, mask_img):
        """First set_mask and the get_masked_data.

        Parameters
        ----------
        mask_img:  nifti-like image, NeuroImage or str
            3D mask array: True where a voxel should be used.
            Can either be:
            - a file path to a Nifti image
            - any object with get_data() and get_affine() methods, e.g., nibabel.Nifti1Image.
            If niimg is a string, consider it as a path to Nifti image and
            call nibabel.load on it. If it is an object, check if get_data()
            and get_affine() methods are present, raise TypeError otherwise.

        Returns
        -------
        The masked data deepcopied
        """
        self.set_mask(mask_img)
        return self.get_data(masked=True, smoothed=True, safe_copy=True)

    def set_mask(self, mask_img):
        """Sets a mask img to this. So every operation to self, this mask will be taken into account.

        Parameters
        ----------
        mask_img: nifti-like image, NeuroImage or str
            3D mask array: True where a voxel should be used.
            Can either be:
            - a file path to a Nifti image
            - any object with get_data() and get_affine() methods, e.g., nibabel.Nifti1Image.
            If niimg is a string, consider it as a path to Nifti image and
            call nibabel.load on it. If it is an object, check if get_data()
            and get_affine() methods are present, raise TypeError otherwise.

        Note
        ----
        self.img and mask_file must have the same shape.

        Raises
        ------
        FileNotFound, NiftiFilesNotCompatible
        """
        mask = load_mask(mask_img, allow_empty=True)
        check_img_compatibility(self.img, mask, only_check_3d=True) # this will raise an exception if something is wrong
        self.mask = mask

    def _mask_data(self, data):
        """Return the data masked with self.mask

        Parameters
        ----------
        data: np.ndarray

        Returns
        -------
        masked np.ndarray

        Raises
        ------
        ValueError if the data and mask dimensions are not compatible.
        Other exceptions related to numpy computations.
        """
        self._check_for_mask()

        msk_data = self.mask.get_data()
        if self.ndim == 3:
            return data[msk_data], np.where(msk_data)
        elif self.ndim == 4:
            return _apply_mask_to_4d_data(data, self.mask)
        else:
            raise ValueError('Cannot mask {} with {} dimensions using mask {}.'.format(self, self.ndim, self.mask))

    def apply_smoothing(self, smooth_fwhm):
        """Set self._smooth_fwhm and then smooths the data.
        See boyle.nifti.smooth.smooth_imgs.

        Returns
        -------
        the smoothed data deepcopied.

        """
        if smooth_fwhm <= 0:
            return

        old_smooth_fwhm   = self._smooth_fwhm
        self._smooth_fwhm = smooth_fwhm
        try:
            data = self.get_data(smoothed=True, masked=True, safe_copy=True)
        except ValueError as ve:
            self._smooth_fwhm = old_smooth_fwhm
            raise
        else:
            self._smooth_fwhm = smooth_fwhm
            return data

    def mask_and_flatten(self):
        """Return a vector of the masked data.

        Returns
        -------
        np.ndarray, tuple of indices (np.ndarray), tuple of the mask shape
        """
        self._check_for_mask()

        return self.get_data(smoothed=True, masked=True, safe_copy=False)[self.get_mask_indices()],\
               self.get_mask_indices(), self.mask.shape

    def unmask(self, arr):
        """Use self.mask to reshape arr and self.img to get an affine and header to create
        a new self.img using the data in arr.
        If self.has_mask() is False, will return the same arr.
        """
        self._check_for_mask()

        if 1 > arr.ndim > 2:
            raise ValueError('The given array has {} dimensions while my mask has {}. '
                             'Masked data must be 1D or 2D array. '.format(arr.ndim,
                                                                           len(self.mask.shape)))

        if arr.ndim == 2:
            return matrix_to_4dvolume(arr, self.mask.get_data())
        elif arr.ndim == 1:
            return vector_to_volume(arr, self.mask.get_data())

    def to_file(self, outpath):
        """Save this object instance in outpath.

        Parameters
        ----------
        outpath: str
            Output file path
        """
        if not self.has_mask() and not self.is_smoothed():
            save_niigz(outpath, self.img)
        else:
            save_niigz(outpath, self.get_data(masked=True, smoothed=True),
                       self.get_header(), self.get_affine())

    def __repr__(self):
        return '<MedicalImage> ' + repr_imgs(self.img)
