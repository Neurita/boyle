# coding=utf-8
"""
A class to manage sets of neuroimage files.
"""
# ------------------------------------------------------------------------------
# Author: Alexandre Manhaes Savio <alexsavio@gmail.com>
# Wrocław University of Technology
#
# 2015, Alexandre Manhaes Savio
# Use this at your own risk!
# ------------------------------------------------------------------------------

import os
import logging
import numpy                         as np
from   six                           import string_types

from   .read              import load_nipy_img, get_img_data, repr_imgs
from   .mask              import load_mask
from   .check             import check_img_compatibility
from   ..files.names      import get_abspath
from   ..more_collections import ItemSet
from   ..storage          import ExportData
from   ..exceptions       import FileNotFound

log = logging.getLogger(__name__)


class NeuroImageSet(ItemSet):
    """A set of NeuroImage samples where each subject is represented by a 3D Nifti file path.

    Each subject image is a boyle.nifti.neuroimage.Neuroimage.

    Parameters
    ----------
    images: list of str or img-like object.
        See NeuroImage constructor docstring.

    mask: str or img-like object.
        See NeuroImage constructor docstring.

    labels: list or tuple of str or int or float.
        This list shoule have the same length as images.

    all_compatible: bool
        True if all the subject files must have the same shape and affine.
    """
    def __init__(self, images, mask=None, labels=None, all_compatible=True):
        self.items  = []
        self.labels = []
        self.others = {}
        self._mask  = load_mask(mask) if mask is not None else None
        self.all_compatible = all_compatible
        try:
            self._load_images_and_labels(images, list(labels))
        except Exception as exc:
            raise Exception('Error initializing NeuroImageSet when loading image set.') from exc

    @property
    def n_subjs(self):
        return len(self.items)

    @property
    def has_mask(self):
        return self.mask is not None

    @property
    def mask(self):
        return self._mask

    @mask.setter
    def mask(self, image):
        """ self.mask setter

        Parameters
        ----------
        image: str or img-like object.
            See NeuroImage constructor docstring.
        """
        if image is None:
            self._mask = None

        try:
            mask = load_mask(image)
        except Exception as exc:
            raise Exception('Could not load mask image {}.'.format(image)) from exc
        else:
            self._mask = mask

    def get_mask_shape(self):
        if self.has_mask:
            return self.mask.shape
        else:
            return None

    def clear_caches(self):
        for img in self.items:
            img.clear_data()

    def check_compatibility(self, one_img, another_img=None):
        """
        Parameters
        ----------
        one_img: str or img-like object.
            See NeuroImage constructor docstring.

        anoter_img: str or img-like object.
            See NeuroImage constructor docstring.
            If None will use the first image of self.images, if there is any.

        Raises
        ------
        NiftiFilesNotCompatible
            If one_img and another_img aren't compatible.

        ValueError
            If another_img is None and there are no other images in this set.
        """
        if another_img is None:
            if len(self.items) > 0:
                another_img = self.items[0]
            else:
                raise ValueError('self.items is empty, need an image to compare '
                                 'with {}'.format(repr_imgs(one_img)))

        try:
            if self.all_compatible:
                check_img_compatibility(one_img, another_img)
            if self.mask is not None:
                check_img_compatibility(one_img, self.mask, only_check_3d=True)
        except:
            raise

    def append_image(self, image, label=None):

        if self.labels and label is None:
            raise ValueError('Label for image {} should be given, but None given.'.format(repr_imgs(image)))

        if self.all_compatible:
            try:
                self.check_compatibility(image)
            except:
                raise

        self.items.append(image)
        if label is not None:
            self.labels.append(label)

    def set_labels(self, labels):
        """
        Parameters
        ----------
        labels: list of int or str
            This list will be checked to have the same size as

        Raises
        ------
        ValueError
            if len(labels) != self.n_subjs
        """
        if not isinstance(labels, string_types) and len(labels) != self.n_subjs:
            raise ValueError('The number of given labels ({}) is not the same '
                             'as the number of subjects ({}).'.format(len(labels), self.n_subjs))

        self.labels = labels

    def _load_images_and_labels(self, images, labels=None):
        """Read the images, load them into self.items and set the labels."""
        if not isinstance(images, (list, tuple)):
            raise ValueError('Expected an iterable (list or tuple) of strings or img-like objects. '
                             'Got a {}.'.format(type(images)))

        if not len(images) > 0:
            raise ValueError('Expected an iterable (list or tuple) of strings or img-like objects '
                             'of size higher than 0. Got {} items.'.format(len(images)))

        if labels is not None and len(labels) != len(images):
            raise ValueError('Expected the same length for image set ({}) and '
                             'labels list ({}).'.format(len(images), len(labels)))

        first_file = images[0]
        if first_file:
            first_img = NeuroImage(first_file)
        else:
            raise('Error reading image {}.'.format(repr_imgs(first_file)))

        for idx, image in enumerate(images):
            try:
                img = NeuroImage(image)
                self.check_compatibility(img, first_img)
            except:
                log.exception('Error reading image {}.'.format(repr_imgs(image)))
                raise
            else:
                self.items.append(img)

        self.set_labels(labels)

    def to_matrix(self, smooth_fwhm=0, outdtype=None):
        """Return numpy.ndarray with the masked or flatten image data and
           the relevant information (mask indices and volume shape).

        Parameters
        ----------
        smooth__fwhm: int
            Integer indicating the size of the FWHM Gaussian smoothing kernel
            to smooth the subject volumes before creating the data matrix

        outdtype: dtype
            Type of the elements of the array, if None will obtain the dtype from
            the first nifti file.

        Returns
        -------
        outmat, mask_indices, vol_shape

        outmat: Numpy array with shape N x prod(vol.shape)
                containing the N files as flat vectors.

        mask_indices: matrix with indices of the voxels in the mask

        vol_shape: Tuple with shape of the volumes, for reshaping.
        """
        if not self.all_compatible:
            raise ValueError("`self.all_compatible` must be True in order to use this function.")

        if not outdtype:
            outdtype = self.items[0].dtype

        # extract some info from the mask
        n_voxels     = None
        mask_indices = None
        mask_shape   = self.items[0].shape[:3]
        if self.has_mask:
            mask_arr     = self.mask.get_data()
            mask_indices = np.nonzero(mask_arr)
            mask_shape   = self.mask.shape
            n_voxels     = np.count_nonzero(mask_arr)

        # if the mask is empty will use the whole image
        if n_voxels is None:
            log.debug('Non-zero voxels have not been found in mask {}'.format(self.mask))
            n_voxels     = np.prod(mask_shape)
            mask_indices = None

        # get the shape of the flattened subject data
        ndims = self.items[0].ndim
        if ndims == 3:
            subj_flat_shape = (n_voxels, )
        elif ndims == 4:
            subj_flat_shape = (n_voxels, self.items[0].shape[3])
        else:
            raise NotImplementedError('The subject images have {} dimensions. '
                                      'Still have not implemented t_matrix for this shape.'.format(ndims))

        # create and fill the big matrix
        outmat = np.zeros((self.n_subjs, ) + subj_flat_shape, dtype=outdtype)
        try:
            for i, image in enumerate(self.items):
                if smooth_fwhm > 0:
                    image.fwhm = smooth_fwhm

                if self.has_mask:
                    image.set_mask(self.mask)

                outmat[i, :], _, _ = image.mask_and_flatten()
                image.clear_data()

        except Exception as exc:
            raise Exception('Error flattening file {0}'.format(image)) from exc
        else:
            return outmat, mask_indices, mask_shape

    def to_file(self, output_file, smooth_fwhm=0, outdtype=None):
        """Save the Numpy array created from to_matrix function to the output_file.

        Will save into the file: outmat, mask_indices, vol_shape and self.others (put here whatever you want)

            data: Numpy array with shape N x prod(vol.shape)
                  containing the N files as flat vectors.

            mask_indices: matrix with indices of the voxels in the mask

            vol_shape: Tuple with shape of the volumes, for reshaping.

        Parameters
        ----------
        output_file: str
            Path to the output file. The extension of the file will be taken into account for the file format.
            Choices of extensions: '.pyshelf' or '.shelf' (Python shelve)
                                   '.mat' (Matlab archive),
                                   '.hdf5' or '.h5' (HDF5 file)

        smooth_fwhm: int
            Integer indicating the size of the FWHM Gaussian smoothing kernel
            to smooth the subject volumes before creating the data matrix

        outdtype: dtype
            Type of the elements of the array, if None will obtain the dtype from
            the first nifti file.
        """
        outmat, mask_indices, mask_shape = self.to_matrix(smooth_fwhm, outdtype)

        exporter = ExportData()
        content = {'data':         outmat,
                   'labels':       self.labels,
                   'mask_indices': mask_indices,
                   'mask_shape':   mask_shape, }

        if self.others:
            content.update(self.others)

        log.debug('Creating content in file {}.'.format(output_file))
        try:
            exporter.save_variables(output_file, content)
        except Exception as exc:
            raise Exception('Error saving variables to file {}.'.format(output_file)) from exc


class NiftiSubjectsSet(ItemSet):
    """A set of subjects where each subject is represented by a 3D Nifti file path.

    Each subject image is a nipy.image.

    Parameters
    ----------
    subj_files: list or dict of str
        file_path -> int/str

    mask_file: str

    all_same_size: bool
        True if all the subject files must have the same shape
    """

    def __init__(self, subj_files, mask_file=None, all_same_shape=True):
        self.items          = []
        self.labels         = []
        self.all_same_shape = all_same_shape
        self.others         = {}
        self.mask_file      = mask_file

        self._init_subj_data(subj_files)

        if all_same_shape:
            self._check_subj_shapes()

    def _init_subj_data(self, subj_files):
        """
        Parameters
        ----------
        subj_files: list or dict of str
            file_path -> int/str
        """
        try:
            if isinstance(subj_files, list):
                self.from_list(subj_files)

            elif isinstance(subj_files, dict):
                self.from_dict(subj_files)
            else:
                raise ValueError('Could not recognize subj_files argument variable type.')
        except Exception as exc:
            raise Exception('Cannot read subj_files input argument.') from exc

    def _check_subj_shapes(self):
        """
        """
        shape      = self.items[0].shape
        mask_shape = self.get_mask_shape()

        for img in self.items:
            if img.shape != shape:
                raise ValueError('Shape mismatch in file {0}.'.format(img.file_path))
            if mask_shape is not None:
                if img.shape != mask_shape:
                    raise ValueError('Shape mismatch in file {0} with mask {1}.'.format(img.file_path,
                                                                                        self.mask_file))

    @staticmethod
    def _load_image(file_path):
        """
        Parameters
        ----------
        file_path: str
            Path to the nifti file

        Returns
        -------
        nipy.Image with a file_path member
        """
        if not os.path.exists(file_path):
            raise FileNotFound(file_path)

        try:
            nii_img           = load_nipy_img(file_path)
            nii_img.file_path = file_path
            return nii_img
        except Exception as exc:
            raise Exception('Reading file {0}.'.format(file_path)) from exc

    @staticmethod
    def _smooth_img(nii_img, smooth_fwhm):
        """
        Parameters
        ----------
        nii_img: nipy.Image

        smooth_fwhm: float

        Returns
        -------
        smoothed nipy.Image
        """
        # delayed import because could not install nipy on Python 3 on OSX
        from   nipy.algorithms.kernel_smooth import LinearFilter

        if smooth_fwhm <= 0:
            return nii_img

        filter = LinearFilter(nii_img.coordmap, nii_img.shape)
        return filter.smooth(nii_img)

    def from_dict(self, subj_files):
        """
        Parameters
        ----------
        subj_files: dict of str
            file_path -> int/str
        """
        for group_label in subj_files:
            try:
                group_files = subj_files[group_label]
                self.items.extend([self._load_image(get_abspath(imgf)) for imgf in group_files])

                self.labels.extend([group_label]*len(group_files))

            except Exception as exc:
                raise Exception('Error while reading files from '
                                'group {0}.'.format(group_label)) from exc

    def from_list(self, subj_files):
        """
        Parameters
        ----------
        subj_files: list of str
            file_paths
        """
        for sf in subj_files:
            try:
                nii_img = self._load_image(get_abspath(sf))
                self.items.append(nii_img)
            except Exception as exc:
                raise Exception('Error while reading file {0}.'.format(sf)) from exc

    @property
    def n_subjs(self):
        return len(self.items)

    @property
    def has_mask(self):
        return self.mask_file is not None

    def get_mask_shape(self):
        if not self.has_mask:
            return None
        return self._load_image(self.mask_file).shape

    def set_labels(self, subj_labels):
        """
        Parameters
        ----------
        subj_labels: list of int or str
            This list will be checked to have the same size as files list
            (self.items)
        """
        if len(subj_labels) != self.n_subjs:
            raise ValueError('The number of given labels is not the same as the number of subjects.')

        self.labels = subj_labels

    def to_matrix(self, smooth_fwhm=0, outdtype=None):
        """Create a Numpy array with the data and return the relevant information (mask indices and volume shape).

        Parameters
        ----------
        smooth_fwhm: int
            Integer indicating the size of the FWHM Gaussian smoothing kernel
            to smooth the subject volumes before creating the data matrix

        outdtype: dtype
            Type of the elements of the array, if None will obtain the dtype from
            the first nifti file.

        Returns
        -------
        outmat, mask_indices, vol_shape

        outmat: Numpy array with shape N x prod(vol.shape)
                containing the N files as flat vectors.

        mask_indices: matrix with indices of the voxels in the mask

        vol_shape: Tuple with shape of the volumes, for reshaping.
        """

        vol = self.items[0].get_data()
        if not outdtype:
            outdtype = vol.dtype

        n_voxels     = None
        mask_indices = None
        mask_shape   = self.items[0].shape

        if self.has_mask:
            mask_arr     = get_img_data(self.mask_file)
            mask_indices = np.where(mask_arr > 0)
            mask_shape   = mask_arr.shape
            n_voxels     = np.count_nonzero(mask_arr)

        if n_voxels is None:
            log.debug('Non-zero voxels have not been found in mask {}'.format(self.mask_file))
            n_voxels = np.prod(vol.shape)

        outmat = np.zeros((self.n_subjs, n_voxels), dtype=outdtype)
        try:
            for i, nipy_img in enumerate(self.items):
                vol = self._smooth_img(nipy_img, smooth_fwhm).get_data()
                if self.has_mask is not None:
                    outmat[i, :] = vol[mask_indices]
                else:
                    outmat[i, :] = vol.flatten()
        except Exception as exc:
            raise Exception('Error when flattening file {0}'.format(nipy_img.file_path)) from exc
        else:
            return outmat, mask_indices, mask_shape

    def to_file(self, output_file, smooth_fwhm=0, outdtype=None):
        """Save the Numpy array created from to_matrix function to the output_file.

        Will save into the file: outmat, mask_indices, vol_shape

            data: Numpy array with shape N x prod(vol.shape)
                  containing the N files as flat vectors.

            mask_indices: matrix with indices of the voxels in the mask

            vol_shape: Tuple with shape of the volumes, for reshaping.

        Parameters
        ----------
        output_file: str
            Path to the output file. The extension of the file will be taken into account for the file format.
            Choices of extensions: '.pyshelf' or '.shelf' (Python shelve)
                                   '.mat' (Matlab archive),
                                   '.hdf5' or '.h5' (HDF5 file)

        smooth_fwhm: int
            Integer indicating the size of the FWHM Gaussian smoothing kernel
            to smooth the subject volumes before creating the data matrix

        # TODO
        #smooth_mask: bool
        #    If True, will smooth the mask with the same kernel.

        outdtype: dtype
            Type of the elements of the array, if None will obtain the dtype from
            the first nifti file.
        """
        outmat, mask_indices, mask_shape = self.to_matrix(smooth_fwhm, outdtype)

        exporter = ExportData()
        content = {'data':         outmat,
                   'labels':       self.labels,
                   'mask_indices': mask_indices,
                   'mask_shape':   mask_shape, }

        if self.others:
            content.update(self.others)

        log.debug('Creating content in file {}.'.format(output_file))

        try:
            exporter.save_variables(output_file, content)
        except Exception as exc:
            raise Exception('Error saving variables to file {}.'.format(output_file)) from exc
