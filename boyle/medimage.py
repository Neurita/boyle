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
import os.path              as op
import numpy                as np

from   .files.names         import get_extension

from   .nifti.neuroimage    import NiftiImage
from   .mhd.read            import load_raw_data_with_mhd, check_mhd_img
from   .mha.read            import

from   .nifti.check         import check_img, check_img_compatibility, repr_imgs
from   .mask                import load_mask, _apply_mask_to_4d_data, vector_to_volume, matrix_to_4dvolume
from   .smooth              import _smooth_data_array
from   .storage             import save_niigz

log = logging.getLogger(__name__)


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


    # generic loader function
    def _load_file(filepath, loader):
        try:
            img = loader(filepath)
        except Exception as ex:
            raise IOError('Could not read {}.'.format(filepath)) from ex
        else:
            return img

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


def _check_medimg(image, make_it_3d=make_it_3d):
    """Check that image is a proper img. Turn filenames into objects.

    Parameters
    ----------
    image: img-like object or str
        Can either be:
        - a file path to a medical image file, e.g. NifTI, .mhd/raw, .mha
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
            img = open_volume_file(image)
        except Exception as ex:
            raise IOError('Error loading image file {}.'.format(image)) from ex
        else:
            if make_it_3d:
                img = _make_it_3d(img)
            return img

    elif isinstance(image, nib.Nifti1Image) or is_img(image):
        return image

    else:
        raise TypeError('Data given cannot be converted to a medical image'
                        ' image: this object -"{}"- does not have'
                        ' get_data or get_affine methods'.format(type(image)))

# TODO
class ImageContainer(object):
    """ A image data container with a `data` and generic `meta_data`.

    Parameters
    ----------
    data: numpy.array

    meta_data
    """
    def __init__(self, data, meta_data):
        self._setup(data, meta_data)

    def _setup(self, data, meta_data):
        raise NotImplementedError('This is under development')

class MedicalImage(object):
    """MedImage is a class that wraps around different formats of medical images (Nifti, RAW, for now)
     offering compatibility with other external tools.

    Note
    ----
    This is under development and probably won't work. Use the helper functions and NiftiImage for now.

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

    Returns
    -------
    result: MedicalImage
       result can be nibabel.Nifti1Image or the input, as-is. It is guaranteed
       that the returned object has get_data() and get_affine() methods.
    """
    def __init__(self, image, make_it_3d=False, cache_data=True):
        self.img      = _check_medimg(image, make_it_3d=make_it_3d)
        self._caching = 'fill' if cache_data else 'unchanged'
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
    def smooth_fwhm(self):
        return self._smooth_fwhm

    def get_filename(self):
        if hasattr(self.img, 'get_filename'):
            return self.img.get_filename()
        return None

    def pixdim(self):
        """ Return the voxel size in the header of the file. """
        return self.get_header().get_zooms()

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
            except:
                raise
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

    def get_affine(self):
        """Return the affine matrix from the image"""
        return self.img.get_affine()

    def get_header(self):
        """Return the header from the image"""
        return self.img.get_header()

    def get_mask_indices(self):
        if self.has_mask():
            return np.where(self.mask.get_data())
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
        try:
            mask = load_mask(mask_img, allow_empty=True)
            check_img_compatibility(self.img, mask, only_check_3d=True)
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
            msk_data = self.mask.get_data()
            if self.ndim == 3:
                return data[msk_data], np.where(msk_data)
            elif self.ndim == 4:
                return _apply_mask_to_4d_data(data, self.mask)
            else:
                msg = 'Cannot mask {} with {} dimensions using mask {}.'.format(self, self.ndim, self.mask)
                log.error(msg)
                raise ValueError(msg)
        except:
            raise

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
        except:
            log.exception('Error smoothing image {} with a {} FWHM mm kernel.'.format(self, smooth_fwhm))
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
        if self.has_mask():
            return self.get_data(smoothed=True, masked=True, safe_copy=False)[self.get_mask_indices()],\
                   self.get_mask_indices(), self.mask.shape
        else:
            log.error('Error flattening image data but this {} has not mask set up.'.format(self))
            return None

    def unmask(self, arr):
        """Use self.mask to reshape arr and self.img to get an affine and header to create
        a new self.img using the data in arr.
        If self.has_mask() is False, will return the same arr.
        """
        if not self.has_mask():
            log.error('Error no mask found to reshape the given array.')
            return arr

        if arr.ndim == 2:
            return matrix_to_4dvolume(arr, self.mask.get_data())
        elif arr.ndim == 1:
            return vector_to_volume(arr, self.mask.get_data())
        else:
            raise ValueError('The given array has {} dimensions while my mask has {}. '
                             'Masked data must be 1D or 2D array. '.format(arr.ndim,
                                                                           len(self.mask.shape)))

    def to_file(self, outpath):
        """Save this object instance in outpath.

        Parameters
        ----------
        outpath: str
            Output file path
        """
        try:
            if not self.has_mask() and not self.is_smoothed():
                save_niigz(outpath, self.img)
            else:
                save_niigz(outpath, self.get_data(masked=True, smoothed=True),
                           self.get_header(), self.get_affine())
        except:
            log.exception('Error saving {} in file {}.'.format(self, outpath))
            raise

    def __repr__(self):
        return '<MedicalImage> ' + repr_imgs(self.img)

    def __str__(self):
        return self.__repr__()
