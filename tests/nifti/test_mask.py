
import os
import os.path as op
import numpy   as np
import nibabel as nib
import boyle
from   boyle.nifti.mask import load_mask, load_mask_data, apply_mask_4d
from   boyle.nifti.read import get_img_data

NI_CLASES = (nib.Nifti1Image, boyle.nifti.NeuroImage)


def test_load_mask_loads():
    mskpath  = op.join(os.environ['FSLDIR'], 'data/standard/MNI152_T1_2mm_brain_mask.nii.gz')
    mask     = load_mask(mskpath)
    assert(isinstance(mask, NI_CLASES))


def test_load_mask_loads_boolean_volume():
    mskpath       = op.join(os.environ['FSLDIR'], 'data/standard/MNI152_T1_2mm_brain_mask.nii.gz')
    mask_data, _  = load_mask_data(mskpath)
    assert(mask_data.dtype == bool)
    assert(len(np.unique(mask_data)) == 2)


def test_apply_mask_4d_applies():
    mskpath = op.join(os.environ['FSLDIR'], 'data/standard/MNI152_T1_3mm_brain_mask.nii.gz')
    imgpath = 'residual_warp.nii.gz'
    if not op.exists(imgpath):
        print('Could not find imgpath to test.')
        assert(False)

    mask_data, affine = load_mask_data(mskpath)
    masked_data, indices, shape = apply_mask_4d(imgpath, mskpath)

    assert(np.sum(mask_data) == masked_data.shape[0])




