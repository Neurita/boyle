# coding=utf-8
#-------------------------------------------------------------------------------

#Author: Alexandre Manhaes Savio <alexsavio@gmail.com>
#Grupo de Inteligencia Computational <www.ehu.es/ccwintco>
#Universidad del Pais Vasco UPV/EHU
#
#2013, Alexandre Manhaes Savio
#Use this at your own risk!
#-------------------------------------------------------------------------------


import logging
import numpy            as np
import scipy.ndimage    as scn
from   collections                  import OrderedDict

from   .check                       import repr_imgs, check_img
from   .read                        import get_img_data, get_img_info
from   .mask                        import create_mask_from
from   ..utils.strings              import search_list


log = logging.getLogger(__name__)


def drain_rois(img):
    """Find all the ROIs in img_data and returns a similar volume with the ROIs
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

    if img_data.ndim == 2:
        kernel = np.ones([3, 3], dtype=int)
    elif img_data.ndim == 3:
        kernel = np.ones([3, 3, 3], dtype=int)
    elif img_data.ndim == 4:
        kernel = np.ones([3, 3, 3, 3], dtype=int)
    else:
        msg = 'Could not build an erosion kernel for image {} with shape {}.'.format(repr_imgs(img),
                                                                                     img_data.shape)
        raise ValueError(msg)

    vals = np.unique(img_data)
    vals = vals[vals != 0]

    for i in vals:
        roi  = img_data == i
        hits = scn.binary_hit_or_miss(roi, kernel)
        roi[hits] = 0
        out[roi > 0] = i

    return out


def create_rois_mask(roislist, filelist):
    """
    Looks for the files in filelist containing the names
    in roislist, these files will be opened, binarised
    and merged in one mask.

    @param roislist: list of strings
    Names of the ROIs, which will have to be in the
    names of the files in filelist.

    @param filelist: list of strings
    List of paths to the volume files containing the ROIs.

    @return: ndarray
    Mask volume
    """
    roifiles = []

    for roi in roislist:
        try:
            roifiles.append(search_list(roi, filelist)[0])
        except Exception as exc:
            log.error(exc)
            raise

    return create_mask_from(roifiles)


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
    atlas_data = check_img(atlas_img)
    rois = np.unique(atlas_data)
    rois = rois[np.nonzero(rois)]
    rois.sort()

    return rois


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


def partition_timeseries(image, roi_img, mask_img, zeroe=True, roi_values=None, outdict=False):
    """Partition the timeseries in tsvol according to the ROIs in roivol.
    If a mask is given, will use it to exclude any voxel outside of it.

    The outdict indicates whether you want a dictionary for each set of timeseries keyed by the ROI value
    or a list of timeseries sets. If True and roi_img is not None will return an OrderedDict, if False
    or roi_img or roi_list is None will return a list.

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
    from   .mask  import load_mask
    from   .read  import read_img
    from   .check import check_img_compatibility

    img  = read_img (image)
    rois = read_img (roi_img)

    # check if roi_img and image are compatible
    try:
        check_img_compatibility(img, rois, only_check_3d=True)
    except:
        log.error('Given image and ROIs image are not compatible.')
        raise

    # check if rois has all roi_values
    roi_data = rois.get_data()
    if roi_values is not None:
        for rv in roi_values:
            if not np.any(roi_data == rv):
                raise ValueError('Could not find value {} in rois_img {}.'.format(rv, repr_imgs(roi_img)))

    # check if mask and image are compatible
    mask = load_mask(mask_img)
    try:
        check_img_compatibility(img, mask, only_check_3d=True)
    except:
        log.error('Given image and mask image are not compatible.')
        raise

    # choose function to call
    if outdict:
        extract_data = _extract_timeseries_dict
    else:
        extract_data = _extract_timeseries_list

    # extract data and return it
    try:
        return extract_data(img.get_data(), rois.get_data(), mask.get_data(), roi_values=roi_values, zeroe=zeroe)
    except:
        raise


def _extract_timeseries_dict(tsvol, roivol, maskvol=None, roi_values=None, zeroe=True):
    """Partition the timeseries in tsvol according to the ROIs in roivol.
    If a mask is given, will use it to exclude any voxel outside of it.

    Parameters
    ----------
    tsvol: numpy.ndarray
        4D timeseries volume

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
    if tsvol.ndim != 4:
        raise ValueError('Expected a timeseries volume with 4 dimensions. tsvol has {} dimensions.'.format(tsvol.ndim))

    if tsvol.shape[:3] != roivol.shape:
        raise ValueError('Expected a ROI volume with the same 3D shape as the timeseries volume. '
                         'In this case, tsvol has shape {} and roivol {}.'.format(tsvol.shape, roivol.shape))

    if maskvol is not None:
        if tsvol.shape[:3] != maskvol.shape:
            raise ValueError('Expected a mask volume with the same 3D shape as the timeseries volume. '
                             'In this case, tsvol has shape {} and maskvol {}.'.format(tsvol.shape, maskvol.shape))

    if roi_values is None:
        roi_values = get_roilist_from_atlas(roivol)

    ts_dict = OrderedDict()

    for r in roi_values:
        if maskvol is not None:
            # get all masked time series within this roi r
            ts = tsvol[(roivol == r) * (maskvol > 0), :]
        else:
            # get all time series within this roi r
            ts = tsvol[roivol == r, :]

        # remove zeroed time series
        if zeroe:
            ts = ts[ts.sum(axis=1) != 0, :]

        if len(ts) == 0:
            ts = np.zeros(tsvol.zeros(tsvol.shape[-1]))

        ts_dict[r] = ts

    return ts_dict


def _extract_timeseries_list(tsvol, roivol, maskvol=None, roi_values=None, zeroe=True):
    """Partition the timeseries in tsvol according to the ROIs in roivol.
    If a mask is given, will use it to exclude any voxel outside of it.

    Parameters
    ----------
    tsvol: numpy.ndarray
        4D timeseries volume

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
    ts_list: list
        A list with the timeseries arrays as items
    """
    if tsvol.ndim != 4:
        raise ValueError('Expected a timeseries volume with 4 dimensions. tsvol has {} dimensions.'.format(tsvol.ndim))

    if tsvol.shape[:3] != roivol.shape:
        raise ValueError('Expected a ROI volume with the same 3D shape as the timeseries volume. '
                         'In this case, tsvol has shape {} and roivol {}.'.format(tsvol.shape, roivol.shape))

    if maskvol is not None:
        if tsvol.shape[:3] != maskvol.shape:
            raise ValueError('Expected a mask volume with the same 3D shape as the timeseries volume. '
                             'In this case, tsvol has shape {} and maskvol {}.'.format(tsvol.shape, maskvol.shape))

    if roi_values is None:
        roi_values = get_roilist_from_atlas(roivol)

    ts_list = []
    for r in roi_values:
        if maskvol is None:
            # get all masked time series within this roi r
            ts = tsvol[(roivol == r) * (maskvol > 0), :]
        else:
            # get all time series within this roi r
            ts = tsvol[roivol == r, :]

        # remove zeroed time series
        if zeroe:
            ts = ts[ts.sum(axis=1) != 0, :]

        if len(ts) == 0:
            ts = np.zeros(tsvol.zeros(tsvol.shape[-1]))

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
        msg = 'Volume in {} does not have 4 dimensions.'.format(repr_imgs(img))
        log.error(msg)
        raise ValueError(msg)

    if not 0 <= vol_idx < img.shape[3]:
        msg = 'IndexError: 4th dimension in volume {} has {} volumes, not {}.'.format(repr_imgs(img), img.shape[3], vol_idx)
        log.error(msg)
        raise IndexError(msg)

    img_data = img.get_data()
    new_vol  = img_data[:, :, :, vol_idx].copy()

    hdr.set_data_shape(hdr.get_data_shape()[:3])

    return new_vol, hdr, aff
