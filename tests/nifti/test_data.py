
import os
import boyle
import os.path as op

fsldir     = os.environ['FSLDIR']
boyledir   = op.realpath(op.join(op.dirname(boyle.__file__), '..'))

msk1path   = op.join(fsldir,   'data', 'standard', 'MNI152_T1_1mm_brain_mask.nii.gz')
msk2path   = op.join(fsldir,   'data', 'standard', 'MNI152_T1_2mm_brain_mask.nii.gz')
msk3path   = op.join(fsldir,   'data', 'standard', 'MNI152_T1_3mm_brain_mask.nii.gz')

brain1path = op.join(fsldir,   'data', 'standard', 'MNI152_T1_1mm_brain.nii.gz')
brain2path = op.join(fsldir,   'data', 'standard', 'MNI152_T1_2mm_brain.nii.gz')
brain3path = op.join(fsldir,   'data', 'standard', 'MNI152_T1_3mm_brain.nii.gz')

std1path   = op.join(fsldir,   'data', 'standard', 'MNI152_T1_1mm.nii.gz')
std2path   = op.join(fsldir,   'data', 'standard', 'MNI152_T1_2mm.nii.gz')
std3path   = op.join(fsldir,   'data', 'standard', 'MNI152_T1_3mm.nii.gz')

img4dpath  = op.join(boyledir, 'data', '4d_img.nii.gz')