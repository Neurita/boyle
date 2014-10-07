
import nibabel as nib
from nipy.algorithms.kernel_smooth import LinearFilter
from nipy import load_image

import logging

log = logging.getLogger(__name__)


def smooth_volume(nifti_file, smoothmm):
    """

    @param nifti_file: string
    @param smoothmm: int
    @return:
    """
    try:
        img = load_image(nifti_file)
    except Exception as exc:
        log.error('Error reading file {0}.'.format(nifti_file), exc_info=True)

    if smoothmm <= 0:
        return img

    filter = LinearFilter(img.coordmap, img.shape)
    return filter.smooth(img)


def create_mask_file(filepath, outpath, threshold=0):
    """

    :param filepath: str
    Path of the nifti input file

    :param threshold: float

    :param outpath: str
     Path to the nifti output file

    """
    from boyle.nifti.storage import save_niigz

    try:
        nibf = nib.load(filepath)
        vol = nibf.get_data() > threshold

        #vol, filepath, affine=None, header=None
        save_niigz(outpath, vol, nibf.get_affine(), nibf.get_header())

    except Exception as exc:
        log.exception('Error creating mask from file {0}.'.format(filepath))





