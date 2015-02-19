import os
import os.path as op
import numpy   as np
from   boyle.nifti      import NeuroImage
from   boyle.nifti.mask import load_mask_data, apply_mask

from   test_data import msk2path, std2path


def test_load_neuroimage():
    nimg     = NeuroImage(msk2path)
    assert(isinstance(nimg, NeuroImage))
    assert(not nimg.has_data_loaded())


def test_neuroimage_load_data():
    nimg = NeuroImage(msk2path)
    _ = nimg.get_data()
    assert(nimg.has_data_loaded())


def test_neuroimage_apply_mask():
    mskpath = msk2path
    stdpath = std2path

    nimg = NeuroImage(stdpath)

    nimg.set_mask(mskpath)
    nimasked_data, _, _ = nimg.mask_and_flatten()
    assert(nimg._is_data_masked)

    masked_data, indices = apply_mask(stdpath, mskpath)

    assert(np.all(masked_data == nimasked_data))


def test_neuroimage_get_masked_data_copies():
    mskpath = msk2path
    stdpath = std2path

    nimg = NeuroImage(stdpath)

    nimg.set_mask(mskpath)
    nimasked_data = nimg.get_data(safe_copy=True)
    assert(not nimg._is_data_masked)

    masked_data = nimg.get_data(masked=False, safe_copy=False)
    assert(not np.all(nimasked_data == masked_data))

    _ = nimg.get_data(masked=True, safe_copy=False)
    assert(nimg._is_data_masked)


def test_neuroimage_smooths():
    stdpath = std2path

    nimg = NeuroImage(stdpath)

    nimg.smooth_fwhm = 10
    smoo10 = nimg.get_data(safe_copy=True)
    assert(not nimg._is_data_smooth)

    nimg.smooth_fwhm = 20
    smoo20 = nimg.get_data(safe_copy=False)
    assert(nimg._is_data_smooth)
    assert(not np.all(smoo10 == smoo20))


def test_neuroimage_to_file():
    mskpath = msk2path
    stdpath = std2path
    outpath = 'test.nii.gz'
    nimg = NeuroImage(stdpath)

    nimg.set_mask(mskpath)

    nimg.to_file(outpath)
    assert(op.exists(outpath))
    os.remove(outpath)

# def test_apply_mask_4d_applies():
#     mskpath = op.join(os.environ['FSLDIR'], 'data/standard/MNI152_T1_3mm_brain_mask.nii.gz')
#     imgpath = 'residual_warp.nii.gz'
#     if not op.exists(imgpath):
#         print('Could not find imgpath to test.')
#         assert(False)
#
#     mask_data, affine = load_mask_data(mskpath)
#     masked_data, indices, shape = apply_mask_4d(imgpath, mskpath)
#
#     assert(np.sum(mask_data) == masked_data.shape[0])

