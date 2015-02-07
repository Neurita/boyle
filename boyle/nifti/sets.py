
import logging
import numpy                         as np
from   nipy.algorithms.kernel_smooth import LinearFilter

from   .read              import load_nipy_img
from   ..files.names      import get_abspath
from   ..more_collections import ItemSet
from   ..storage          import ExportData
from   ..exceptions       import FileNotFound, NiftiFilesNotCompatible


log = logging.getLogger(__name__)


class NiftiSubjectsSet(ItemSet):
    """A set of subjects where each subject is represented by a Nifti file path.

    Parameters
    ----------
    subj_files: list or dict of str
        file_path -> int/str

    mask_file: str

    all_same_size: bool
        True if all the subject files must have the same shape
    """

    def __init__(self, subj_files, mask_file=None, all_same_shape=True):
        self.items = []
        self.labels = []
        self.all_same_shape = all_same_shape

        self.mask_file = mask_file
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
            log.exception('Cannot read subj_files input argument')

    def _check_subj_shapes(self):
        """
        """
        shape = self.items[0].shape

        mask_shape = self.get_mask_shape()

        for img in self.items:
            if img.shape != shape:
                raise ValueError('Shape mismatch in file {0}.'.format(img.file_path))
            if mask_shape is not None:
                if img.shape != mask_shape:
                    raise ValueError('Shape mismatch in file {0} with mask {1}.'.format(img.file_path, self.mask_file))

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
            nii_img = load_nipy_img(file_path)
            nii_img.file_path = file_path
            return nii_img
        except Exception as exc:
            log.exception('Reading file {0}.'.format(file_path))
            raise

    @staticmethod
    def _smooth_img(nii_img, smooth_mm):
        """
        Parameters
        ----------
        nii_img: nipy.Image

        Returns
        -------
        smoothed nipy.Image
        """
        if smooth_mm <= 0:
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
                log.exception('Error while reading files from '
                              'group {0}.'.format(group_label))

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
                log.exception('Error while reading file {0}.'.format(sf))

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
            log.error('The number of given labels is not the same '
                      'as the number of subjects.')

        self.labels = subj_labels

    def to_matrix(self, smooth_mm=0, smooth_mask=False, outdtype=None):
        """Create a Numpy array with the data and return the relevant information (mask indices and volume shape).

        Parameters
        ----------
        smooth__mm: int
            Integer indicating the size of the FWHM Gaussian smoothing kernel
            to smooth the subject volumes before creating the data matrix

        smooth_mask: bool
            If True, will smooth the mask with the same kernel.

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

        n_voxels = None
        mask_indices = None
        mask_shape = None

        if self.has_mask:
            mask = load_nipy_img(self.mask_file)

            if smooth_mask:
                mask = self._smooth_img(mask, smooth_mm)

            mask = mask.get_data()
            mask_indices = np.where(mask > 0)
            mask_shape = mask.shape
            n_voxels = np.count_nonzero(mask)

        if n_voxels is None:
            log.debug('Non-zero voxels have not been found in mask {}'.format(self.mask_file))
            n_voxels = np.prod(vol.shape)

        outmat = np.zeros((self.n_subjs, n_voxels), dtype=outdtype)
        try:
            for i, nipy_img in enumerate(self.items):
                vol = self._smooth_img(nipy_img, smooth_mm).get_data()
                if mask_indices is not None:
                    outmat[i, :] = vol[mask_indices]
                else:
                    outmat[i, :] = vol.flatten()
        except Exception as exc:
            log.exception('Flattening file {0}'.format(nipy_img.file_path))
            raise
        else:
            return outmat, mask_indices, mask_shape

    def to_file(self, output_file, smooth_mm=0, smooth_mask=False, outdtype=None):
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

        smooth__mm: int
            Integer indicating the size of the FWHM Gaussian smoothing kernel
            to smooth the subject volumes before creating the data matrix

        smooth_mask: bool
            If True, will smooth the mask with the same kernel.

        outdtype: dtype
            Type of the elements of the array, if None will obtain the dtype from
            the first nifti file.
        """
        try:
            outmat, mask_indices, mask_shape = self.to_matrix(smooth_mm, smooth_mask, outdtype)
        except:
            log.exception('Error creating data matrix.')
            raise

        exporter = ExportData()
        content = {'data':         outmat,
                   'mask_indices': mask_indices,
                   'mask_shape':   mask_shape,}

        log.debug('Creating content in file {}.'.format(output_file))

        try:
            exporter.save_variables(output_file, content)
        except:
            log.exception('Error saving variables to file {}.'.format(output_file))
            raise
