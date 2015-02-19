
from   boyle.nifti.read import read_img
from   test_data import msk2path


def test_read_img_reads_path():
    img     = read_img(msk2path)
    assert(img is not None)


def test_read_img_reads_img():
    imgp  = read_img(msk2path)

    img = read_img(imgp)
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

