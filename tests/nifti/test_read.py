
import os
import os.path as op
from   boyle.nifti.read import vector_to_volume, read_img


def test_read_img_reads_file():
    imgpath = op.join(os.environ['FSLDIR'], 'data/standard/MNI152_T1_2mm_brain_mask.nii.gz')
    img     = read_img(imgpath)
    assert(img is not None)


def test_read_img_reads_img():
    imgpath = op.join(os.environ['FSLDIR'], 'data/standard/MNI152_T1_2mm_brain_mask.nii.gz')
    img  = read_img(imgpath)

    img = read_img(img)
    assert(img is not None)


def test_read_img_raises():
    #imgpath = op.join(os.environ['FSLDIR'], 'data/standard/MNI152_T1_2mm_brain_mask')
    #assert_raises(read_img(imgpath))
    pass


def test_vector_to_volume():
    pass
    # imgpath = op.join(os.environ['FSLDIR'], 'data/standard/MNI152_T1_2mm_brain_mask.nii.gz')
    # img     = load_img(imgpath)
    # ass
    # vol     = img.get_data()
    # anat = nib.load('/usr/share/fsl/data/standard/MNI152_T1_2mm_brain.nii.gz')
    # anatvol = anat.get_data()
    # anatvol[np.where(vol > 0)]
    # vec = anatvol[np.where(vol > 0)]
    # vector_to_volume(vec, np.where(vol > 0), vol.shape)

