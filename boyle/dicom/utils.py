# coding=utf-8
"""
Utilities for Dicom file management.
"""
# ------------------------------------------------------------------------------
# Author: Alexandre Manhaes Savio <alexsavio@gmail.com>
#
# 2015, Alexandre Manhaes Savio
# Use this at your own risk!
# ------------------------------------------------------------------------------

import os
import os.path as op
import logging
from   collections   import defaultdict

import pydicom as dicom
from   dicom.dataset import FileDataset

from ..files.search import get_all_files

log = logging.getLogger(__name__)


class DicomFile(FileDataset):
    """Store the contents of a DICOM file

    Parameters
    ----------
    file_path: str
     Full path and filename to the file.
     Use None if is a BytesIO.

    header_fields: subset of DICOM header fields to be
     stored here, the rest will be ignored.

    dataset: dict
     Some form of dictionary, usually a Dataset from read_dataset()

    preamble: the 128-byte DICOM preamble

    file_meta: dataset
     The file meta info dataset, as returned by _read_file_meta,
     or an empty dataset if no file meta information is in the file

    is_implicit_VR: bool
     True if implicit VR transfer syntax used; False if explicit VR.
     Default is True.

    is_little_endian: bool
     True if little-endian transfer syntax used; False if big-endian.
     Default is True.
    """
    def __init__(self, file_path, preamble=None, file_meta=None,
                 is_implicit_VR=True, is_little_endian=True):
        try:
            dcm = dicom.read_file(file_path, force=True)

            FileDataset.__init__(self, file_path, dcm, preamble, file_meta,
                                 is_implicit_VR, is_little_endian)

            self.file_path = op.abspath(file_path)

        except Exception as exc:
            log.exception('Error reading file {0}.'.format(file_path))
            raise

    def get_attributes(self, attributes, default=''):
        """Return the attributes values from this DicomFile

        Parameters
        ----------
        attributes: str or list of str
         DICOM field names

        default: str
         Default value if the attribute does not exist.

        Returns
        -------
        Value of the field or list of values.
        """
        if isinstance(attributes, str):
            attributes = [attributes]

        attrs = [getattr(self, attr, default) for attr in attributes]

        if len(attrs) == 1:
            return attrs[0]

        return tuple(attrs)


def get_dicom_files(dirpath):
    return [DicomFile(os.path.join(dp, f))
            for dp, dn, filenames in os.walk(dirpath)
            for f in filenames if is_dicom_file(os.path.join(dp, f))]


def get_unique_field_values(dcm_file_list, field_name):
    """Return a set of unique field values from a list of DICOM files

    Parameters
    ----------
    dcm_file_list: iterable of DICOM file paths

    field_name: str
     Name of the field from where to get each value

    Returns
    -------
    Set of field values
    """
    field_values = set()
    try:
        for dcm in dcm_file_list:
            field_values.add(str(DicomFile(dcm).get_attributes(field_name)))
        return field_values
    except Exception:
        log.exception('Error reading file {}'.format(dcm))
        raise


def find_all_dicom_files(root_path):
    """
    Returns a list of the dicom files within root_path

    Parameters
    ----------
    root_path: str
    Path to the directory to be recursively searched for DICOM files.

    Returns
    -------
    dicoms: set
    Set of DICOM absolute file paths
    """
    dicoms = set()
    f = None
    try:
        for fpath in get_all_files(root_path):
            if is_dicom_file(fpath):
                dicoms.add(fpath)
    except Exception as exc:
        log.exceptions('Error reading file {0}.'.format(fpath))

    return dicoms


def is_dicom_file(filepath):
    """
    Tries to read the file using dicom.read_file,
    if the file exists and dicom.read_file does not raise
    and Exception returns True. False otherwise.

    :param filepath: str
     Path to DICOM file

    :return: bool
    """
    if not os.path.exists(filepath):
        return False

    filename = os.path.basename(filepath)
    if filename == 'DICOMDIR':
        return False

    try:
        _ = dicom.read_file(filepath)
    except Exception as exc:
        log.debug('Checking if {0} was a DICOM, but returned '
                  'False.'.format(filepath))
        return False

    return True


def group_dicom_files(dicom_paths, hdr_field='PatientID'):
    """Group in a dictionary all the DICOM files in dicom_paths
    separated by the given `hdr_field` tag value.

    Parameters
    ----------
    dicom_paths: str
        Iterable of DICOM file paths.

    hdr_field: str
        Name of the DICOM tag whose values will be used as key for the group.

    Returns
    -------
    dicom_groups: dict of dicom_paths
    """
    dicom_groups = defaultdict(list)
    try:
        for dcm in dicom_paths:
            hdr = dicom.read_file(dcm)
            group_key = getattr(hdr, hdr_field)
            dicom_groups[group_key].append(dcm)
    except Exception as exc:
        log.exception('Error reading file {0}.'.format(dcm))

    return dicom_groups


if __name__ == '__main__':

    from boyle.dicom.utils import DicomFile

    dcm_file_hd = '/home/alexandre/Projects/bcc/macuto/macuto/dicom/subj1_01.IMA'
    #%timeit DicomFile(dcm_file_hd)
    #1000 loops, best of 3: 1.75 ms per loop

    dcm_file_ssd = '/scratch/subj1_01.IMA'
    #%timeit DicomFile(dcm_file_ssd)
    #1000 loops, best of 3: 1.75 ms per loop
