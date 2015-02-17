# coding=utf-8
"""
A class to manage neuroimage files. A wrapper around nibabel and nipy for own purposes.
"""
# ------------------------------------------------------------------------------
# Author: Alexandre Manhaes Savio <alexsavio@gmail.com>
# Wrocław University of Technology
#
# 2015, Alexandre Manhaes Savio
# Use this at your own risk!
# ------------------------------------------------------------------------------

import gc
import logging
import numpy    as np

from   .check   import check_img, check_img_compatibility, repr_imgs
from   .read    import get_data, get_img_data
from   .mask    import load_mask, _apply_mask_to_4d_data
from   .smooth  import smooth_img
from   .storage import save_niigz

log = logging.getLogger(__name__)


class NeuroImage(object):
    """NeuroImage is a class that wraps around nibabel and nipy functionality and offers compatibility with
    other external tools.

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

    Memory Test
    -----------
    >>> %load_ext memory_profiler
    >>> import os
    >>> import os.path as op
    >>> from boyle.nifti import NeuroImage as ni
    >>> import nibabel as nib

    >>> fpath = op.join(os.environ.get('FSLDIR', None), 'data/standard/MNI152_T1_1mm_brain.nii.gz')
    >>> %memit nib.load(fpath).get_data()
    >>> %memit ni(fpath).get_data()
    """
    def __init__(self, image, make_it_3d=False, cache_data=True):
        self.img         = check_img(image, make_it_3d=make_it_3d)
        self._caching    = 'fill' if cache_data else 'unchanged'
        self.mask        = None
        self.data        = None
        self.smooth_fwhm = None
        self._is_data_masked = False

    def clear(self):
        self.mask = None
        self.clear_data()

    def clear_data(self):
        self.data = None
        self._is_data_masked = False
        gc.collect()

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

    def has_data_loaded(self):
        return self.data is not None

    def get_filename(self):
        if hasattr(self.img, 'get_filename'):
            return self.img.get_filename()
        return None

    def has_mask(self):
        return self.mask is not None

    def get_data(self, masked=True, safe_copy=False):
        """Get the data in the image.
         If save_copy is True, will perform a deep copy of the data and return it.

        Parameters
        ----------
        masked: (optional) bool
            If True and self.has_mask will return the masked data, the whole data otherwise.

        safe_copy: (optional) bool

        Returns
        -------
        np.ndarray
        """
        if self.has_data_loaded() and not safe_copy and masked == self._is_data_masked:
            return self.data

        if safe_copy:
            data = get_data(self.img)
        else:
            data = self.img.get_data(caching=self._caching)

        is_data_masked = False
        if masked and self.has_mask():
            try:
                data = self._mask_data(data)
                is_data_masked = True
            except ValueError:
                pass
            except:
                msg = 'Error masking data file {} with mask {}'.format(self, repr_imgs(self.mask))
                log.exception(msg)
                return None

        if not safe_copy:
            self.data = data
            self._is_data_masked = is_data_masked

        return data

    def get_affine(self):
        """Return the affine matrix from the image"""
        return self.img.get_affine()

    def get_header(self):
        """Return the header from the image"""
        return self.img.get_header()

    def get_mask_indices(self):
        if self.has_mask():
            return np.where(get_img_data(self.mask))
        else:
            log.error('Error looking for mask_indices but this {} has not mask set up.'.format(self))
            return None

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
        vol[mask_indices], mask_indices, mask.shape
        """
        self.set_mask(mask_img)
        return self.get_masked_data()

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
        try:
            mask = load_mask(mask_img, allow_empty=True)
            check_img_compatibility(self.img, mask)
        except:
            log.exception('Error setting up mask {} for {}.'.format(repr_imgs(mask_img), self))
            raise
        else:
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
        try:
            if self.ndim == 3:
                return data[self.mask]
            elif self.ndim == 4:
                return _apply_mask_to_4d_data(data, self.mask)
            else:
                msg = 'Cannot mask {} with {} dimensions using mask {}.'.format(self, self.ndim, self.mask)
                log.error(msg)
                raise ValueError(msg)
        except:
            raise

    def get_masked_data(self):
        """Return the voxels in self.img that are within the self.mask, the mask indices
        and the mask shape. This works either if self.img is 3D or 4D data. If it is 4D, will apply
        the 3D mask to every

        Returns
        -------
        vol[mask_indices]
        """
        try:
            return self.get_data(masked=True, safe_copy=True)
        except:
            log.exception('Error extracting data from {1} using mask {0}.'.format(repr_imgs(self.mask), self))
            return None

    def mask_flatten(self):
        """Return a vector of the masked data.

        Returns
        -------
        np.ndarray, tuple of indices (np.ndarray), tuple of the mask shape

        """
        if self.has_mask():
            return self.get_data()[self.mask], np.where(get_img_data(self.mask)), self.mask.shape
        else:
            log.error('Error flattening image data but this {} has not mask set up.'.format(self))
            return None

    def smooth(self, smooth_fwhm):
        """See boyle.nifti.smooth.smooth_img"""
        try:
            img = smooth_img([self.img], fwhm=smooth_fwhm)
        except:
            log.error('Error smoothing image {} with a {} FWHM mm kernel.'.format(self, smooth_fwhm))
            raise
        else:
            self.img = img
            self.smooth_fwhm = smooth_fwhm

    # TODO
    # def unmask(self, arr):
    #     """Use self.mask to reshape arr and self.img to get an affine and header to create a new self.img using
    #     the data in arr.
    #     """

    def to_file(self, outpath):
        """Save this object instance in outpath.

        Parameters
        ----------
        outpath: str
            Output file path
        """
        try:
            if not self.has_mask():
                save_niigz(outpath, self.img)
            else:
                save_niigz(outpath, self.get_data(masked=True), self.get_header(), self.get_affine())
        except:
            log.exception('Error saving {} in file {}.'.format(self, outpath))
            raise

    def __repr__(self):
        return '<NeuroImage> ' + repr_imgs(self.img)

    def __str__(self):
        return self.__repr__()