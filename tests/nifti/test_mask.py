
import numpy   as np
import nibabel as nib
import boyle
from   boyle.nifti.read import read_img
from   boyle.nifti.mask import load_mask, load_mask_data
from   boyle.nifti.mask import apply_mask, apply_mask_4d
from   boyle.nifti.mask import vector_to_volume, matrix_to_4dvolume
from   test_data import msk2path, msk3path, brain2path, img4dpath

NI_CLASES = (nib.Nifti1Image, boyle.nifti.NeuroImage)


def test_load_mask_loads():
    mask     = load_mask(msk2path)
    assert(isinstance(mask, boyle.nifti.NeuroImage))


def test_load_mask_loads_boolean_volume():
    mask_data, _  = load_mask_data(msk2path)
    assert(mask_data.dtype == bool)
    assert(len(np.unique(mask_data)) == 2)


def test_apply_mask_4d_applies():
    mask_data, affine = load_mask_data(msk3path)
    masked_data, indices = apply_mask_4d(img4dpath, msk3path)

    assert(np.sum(mask_data) == masked_data.shape[0])


def test_vector_to_volume():
    stdpath = brain2path
    mskpath = msk2path

    msk = read_img(mskpath)
    std = read_img(stdpath)

    data, mask = apply_mask(std, msk)

    vol = vector_to_volume (data, mask)
    np.testing.assert_equal(std.shape,      vol.shape)
    np.testing.assert_equal(std.get_data(), vol)


def test_matrix_to_4dvolume():
    stdpath = img4dpath
    mskpath = msk3path

    msk = read_img(mskpath)
    std = read_img(stdpath)

    data, mask = apply_mask_4d(std,       msk)
    vol = matrix_to_4dvolume  (data,      mask)
    np.testing.assert_equal   (vol.shape, std.shape)



