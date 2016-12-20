# coding=utf-8

# -------------------------------------------------------------------------------
# Author: Alexandre Manhães Savio <alexsavio@gmail.com>
# Grupo de Inteligencia Computational <www.ehu.es/ccwintco>
# Universidad del Pais Vasco UPV/EHU
#
# 2013, Alexandre Manhaes Savio
# Use this at your own risk!
# -------------------------------------------------------------------------------

import numpy            as np
import scipy.ndimage    as scn
from   collections      import OrderedDict

from   .check           import check_img_compatibility, repr_imgs, check_img
from   .read            import read_img, get_img_data, get_img_info
from   .mask            import binarise, load_mask
from   ..utils.strings  import search_list


def drain_rois(img):
    """Find all the ROIs in img and returns a similar volume with the ROIs
    emptied, keeping only their border voxels.

    This is useful for DTI tractography.

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
    np.ndarray
        an array of same shape as img_data
    """
    img_data = get_img_data(img)

    out = np.zeros(img_data.shape, dtype=img_data.dtype)

    krn_dim = [3] * img_data.ndim
    kernel  = np.ones(krn_dim, dtype=int)

    vals = np.unique(img_data)
    vals = vals[vals != 0]

    for i in vals:
        roi  = img_data == i
        hits = scn.binary_hit_or_miss(roi, kernel)
        roi[hits] = 0
        out[roi > 0] = i

    return out


def largest_connected_component(volume):
    """Return the largest connected component of a 3D array.

    Parameters
    -----------
    volume: numpy.array
        3D boolean array.

    Returns
    --------
    volume: numpy.array
        3D boolean array with only one connected component.
    """
    # We use asarray to be able to work with masked arrays.
    volume = np.asarray(volume)
    labels, num_labels = scn.label(volume)
    if not num_labels:
        raise ValueError('No non-zero values: no connected components found.')

    if num_labels == 1:
        return volume.astype(np.bool)

    label_count = np.bincount(labels.ravel().astype(np.int))
    # discard the 0 label
    label_count[0] = 0
    return labels == label_count.argmax()


def large_clusters_mask(volume, min_cluster_size):
    """ Return as mask for `volume` that includes only areas where
    the connected components have a size bigger than `min_cluster_size`
    in number of voxels.

    Parameters
    -----------
    volume: numpy.array
        3D boolean array.

    min_cluster_size: int
        Minimum size in voxels that the connected component must have.

    Returns
    --------
    volume: numpy.array
        3D int array with a mask excluding small connected components.
    """
    labels, num_labels = scn.label(volume)

    labels_to_keep = set([i for i in range(num_labels)
                         if np.sum(labels == i) >= min_cluster_size])

    clusters_mask = np.zeros_like(volume, dtype=int)
    for l in range(num_labels):
        if l in labels_to_keep:
            clusters_mask[labels == l] = 1

    return clusters_mask


def create_rois_mask(roislist, filelist):
    """Look for the files in filelist containing the names in roislist, these files will be opened, binarised
    and merged in one mask.

    Parameters
    ----------
    roislist: list of strings
        Names of the ROIs, which will have to be in the names of the files in filelist.

    filelist: list of strings
        List of paths to the volume files containing the ROIs.

    Returns
    -------
    numpy.ndarray
        Mask volume
    """
    roifiles = []

    for roi in roislist:
        try:
            roi_file = search_list(roi, filelist)[0]
        except Exception as exc:
            raise Exception('Error creating list of roi files. \n {}'.format(str(exc)))
        else:
            roifiles.append(roi_file)

    return binarise(roifiles)


def get_unique_nonzeros(arr):
    """ Return a sorted list of the non-zero unique values of arr.

    Parameters
    ----------
    arr: numpy.ndarray
        The data array

    Returns
    -------
    list of items of arr.
    """
    rois = np.unique(arr)
    rois = rois[np.nonzero(rois)]
    rois.sort()

    return rois


def get_roilist_from_atlas(atlas_img):
    """
    Extract unique values from the atlas and returns them as an ordered list.

    Parameters
    ----------
    atlas_img: img-like object or str
        Volume defining different ROIs.
        Can either be:
        - a file path to a Nifti image
        - any object with get_data() and get_affine() methods, e.g., nibabel.Nifti1Image.
        If niimg is a string, consider it as a path to Nifti image and
        call nibabel.load on it. If it is an object, check if get_data()
        and get_affine() methods are present, raise TypeError otherwise.

    Returns
    -------
    np.ndarray
        An 1D array of roi values from atlas volume.

    Note
    ----
    The roi with value 0 will be considered background so will be removed.
    """
    return get_unique_nonzeros(check_img(atlas_img).get_data())


def get_rois_centers_of_mass(vol):
    """Get the center of mass for each ROI in the given volume.

    Parameters
    ----------
    vol: numpy ndarray
        Volume with different values for each ROI.

    Returns
    -------
    OrderedDict
        Each entry in the dict has the ROI value as key and the center_of_mass coordinate as value.
    """
    from scipy.ndimage.measurements import center_of_mass

    roisvals = np.unique(vol)
    roisvals = roisvals[roisvals != 0]

    rois_centers = OrderedDict()
    for r in roisvals:
        rois_centers[r] = center_of_mass(vol, vol, r)

    return rois_centers


def partition_timeseries(image, roi_img, mask_img=None, zeroe=True, roi_values=None, outdict=False):
    """Partition the timeseries in tsvol according to the ROIs in roivol.
    If a mask is given, will use it to exclude any voxel outside of it.

    The outdict indicates whether you want a dictionary for each set of timeseries keyed by the ROI value
    or a list of timeseries sets. If True and roi_img is not None will return an OrderedDict, if False
    or roi_img or roi_list is None will return a list.

    Background value is assumed to be 0 and won't be used here.

    Parameters
    ----------
    image: img-like object or str
        4D timeseries volume

    roi_img: img-like object or str
        3D volume defining different ROIs.

    mask_img: img-like object or str
        3D mask volume

    zeroe: bool
        If true will remove the null timeseries voxels.

    roi_values: list of ROI values (int?)
        List of the values of the ROIs to indicate the
        order and which ROIs will be processed.

    outdict: bool
        If True will return an OrderedDict of timeseries sets, otherwise a list.

    Returns
    -------
    timeseries: list or OrderedDict
        A dict with the timeseries as items and keys as the ROIs voxel values or
        a list where each element is the timeseries set ordered by the sorted values in roi_img or by the roi_values
        argument.

    """
    img  = read_img(image)
    rois = read_img(roi_img)

    # check if roi_img and image are compatible
    check_img_compatibility(img, rois, only_check_3d=True)

    # check if rois has all roi_values
    roi_data = rois.get_data()
    if roi_values is not None:
        for rv in roi_values:
            if not np.any(roi_data == rv):
                raise ValueError('Could not find value {} in rois_img {}.'.format(rv, repr_imgs(roi_img)))
    else:
        roi_values = get_unique_nonzeros(roi_data)

    # check if mask and image are compatible
    if mask_img is None:
        mask_data = None
    else:
        mask = load_mask(mask_img)
        check_img_compatibility(img, mask, only_check_3d=True)
        mask_data = mask.get_data()

    # choose function to call
    if outdict:
        extract_data = _extract_timeseries_dict
    else:
        extract_data = _extract_timeseries_list

    # extract data and return it
    try:
        return extract_data(img.get_data(), rois.get_data(), mask_data,
                            roi_values=roi_values, zeroe=zeroe)
    except:
        raise


def partition_volume(*args, **kwargs):
    """ Look at partition_timeseries function docstring. """
    return partition_timeseries(*args, **kwargs)


def _check_for_partition(datavol, roivol, maskvol=None):
    if datavol.ndim != 4 and datavol.ndim != 3:
        raise AttributeError('Expected a volume with 3 or 4 dimensions. '
                             '`datavol` has {} dimensions.'.format(datavol.ndim))

    if datavol.shape[:3] != roivol.shape:
        raise AttributeError('Expected a ROI volume with the same 3D shape as the timeseries volume. '
                             'In this case, datavol has shape {} and roivol {}.'.format(datavol.shape, roivol.shape))

    if maskvol is not None:
        if datavol.shape[:3] != maskvol.shape:
            raise AttributeError('Expected a mask volume with the same 3D shape as the timeseries volume. '
                                 'In this case, datavol has shape {} and maskvol {}.'.format(datavol.shape,
                                                                                             maskvol.shape))


def _partition_data(datavol, roivol, roivalue, maskvol=None, zeroe=True):
    """ Extracts the values in `datavol` that are in the ROI with value `roivalue` in `roivol`.
    The ROI can be masked by `maskvol`.

    Parameters
    ----------
    datavol: numpy.ndarray
        4D timeseries volume or a 3D volume to be partitioned

    roivol: numpy.ndarray
        3D ROIs volume

    roivalue: int or float
        A value from roivol that represents the ROI to be used for extraction.

    maskvol: numpy.ndarray
        3D mask volume

    zeroe: bool
        If true will remove the null timeseries voxels.  Only applied to timeseries (4D) data.

    Returns
    -------
    values: np.array
        An array of the values in the indicated ROI.
        A 2D matrix if `datavol` is 4D or a 1D vector if `datavol` is 3D.
    """
    if maskvol is not None:
        # get all masked time series within this roi r
        indices = (roivol == roivalue) * (maskvol > 0)
    else:
        # get all time series within this roi r
        indices = roivol == roivalue

    if datavol.ndim == 4:
        ts = datavol[indices, :]
    else:
        ts = datavol[indices]

    # remove zeroed time series
    if zeroe:
        if datavol.ndim == 4:
            ts = ts[ts.sum(axis=1) != 0, :]

    return ts


def _extract_timeseries_dict(tsvol, roivol, maskvol=None, roi_values=None, zeroe=True):
    """Partition the timeseries in tsvol according to the ROIs in roivol.
    If a mask is given, will use it to exclude any voxel outside of it.

    Parameters
    ----------
    tsvol: numpy.ndarray
        4D timeseries volume or a 3D volume to be partitioned

    roivol: numpy.ndarray
        3D ROIs volume

    maskvol: numpy.ndarray
        3D mask volume

    zeroe: bool
        If true will remove the null timeseries voxels.

    roi_values: list of ROI values (int?)
        List of the values of the ROIs to indicate the
        order and which ROIs will be processed.

    Returns
    -------
    ts_dict: OrderedDict
        A dict with the timeseries as items and keys as the ROIs voxel values.
    """
    _check_for_partition(tsvol, roivol, maskvol)

    # get unique values of the atlas
    if roi_values is None:
        roi_values = get_unique_nonzeros(roivol)

    ts_dict = OrderedDict()
    for r in roi_values:
        ts = _partition_data(tsvol, roivol, r, maskvol, zeroe)

        if len(ts) == 0:
            ts = np.zeros(tsvol.shape[-1])

        ts_dict[r] = ts

    return ts_dict


def _extract_timeseries_list(tsvol, roivol, maskvol=None, roi_values=None, zeroe=True):
    """Partition the timeseries in tsvol according to the ROIs in roivol.
    If a mask is given, will use it to exclude any voxel outside of it.

    Parameters
    ----------
    tsvol: numpy.ndarray
        4D timeseries volume or a 3D volume to be partitioned

    roivol: numpy.ndarray
        3D ROIs volume

    maskvol: numpy.ndarray
        3D mask volume

    zeroe: bool
        If true will remove the null timeseries voxels. Only applied to timeseries (4D) data.

    roi_values: list of ROI values (int?)
        List of the values of the ROIs to indicate the
        order and which ROIs will be processed.

    Returns
    -------
    ts_list: list
        A list with the timeseries arrays as items
    """
    _check_for_partition(tsvol, roivol, maskvol)

    if roi_values is None:
        roi_values = get_unique_nonzeros(roivol)

    ts_list = []
    for r in roi_values:
        ts = _partition_data(tsvol, roivol, r, maskvol, zeroe)

        if len(ts) == 0:
            ts = np.zeros(tsvol.shape[-1])

        ts_list.append(ts)

    return ts_list


def get_3D_from_4D(image, vol_idx=0):
    """Pick one 3D volume from a 4D nifti image file

    Parameters
    ----------
    image: img-like object or str
        Volume defining different ROIs.
        Can either be:
        - a file path to a Nifti image
        - any object with get_data() and get_affine() methods, e.g., nibabel.Nifti1Image.
        If niimg is a string, consider it as a path to Nifti image and
        call nibabel.load on it. If it is an object, check if get_data()
        and get_affine() methods are present, raise TypeError otherwise.

    vol_idx: int
        Index of the 3D volume to be extracted from the 4D volume.

    Returns
    -------
    vol, hdr, aff
        The data array, the image header and the affine transform matrix.
    """
    img      = check_img(image)
    hdr, aff = get_img_info(img)

    if len(img.shape) != 4:
        raise AttributeError('Volume in {} does not have 4 dimensions.'.format(repr_imgs(img)))

    if not 0 <= vol_idx < img.shape[3]:
        raise IndexError('IndexError: 4th dimension in volume {} has {} volumes, '
                         'not {}.'.format(repr_imgs(img), img.shape[3], vol_idx))

    img_data = img.get_data()
    new_vol  = img_data[:, :, :, vol_idx].copy()

    hdr.set_data_shape(hdr.get_data_shape()[:3])

    return new_vol, hdr, aff
