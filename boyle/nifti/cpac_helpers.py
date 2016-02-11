# coding=utf-8
# -------------------------------------------------------------------------------
# Author: Alexandre Manhaes Savio <alexsavio@gmail.com>
# Grupo de Inteligencia Computational <www.ehu.es/ccwintco>
# Universidad del Pais Vasco UPV/EHU
#
# 2015, Alexandre Manhaes Savio
# Use this at your own risk!
# -------------------------------------------------------------------------------

import logging
import os.path       as op
from   ..commands    import check_call
from   ..files.names import remove_ext, get_extension

log = logging.getLogger(__name__)


def xfm_atlas_to_functional(atlas_filepath, anatbrain_filepath, meanfunc_filepath,
                            atlas2anat_nonlin_xfm_filepath, is_atlas2anat_inverted,
                            anat2func_lin_xfm_filepath,
                            atlasinanat_out_filepath, atlasinfunc_out_filepath,
                            interp='nn', rewrite=True, parallel=False):
    """Call FSL tools to apply transformations to a given atlas to a functional image.
    Given the transformation matrices.

    Parameters
    ----------
    atlas_filepath: str
        Path to the 3D atlas volume file.

    anatbrain_filepath: str
        Path to the anatomical brain volume file (skull-stripped and registered to the same space as the atlas,
        e.g., MNI).

    meanfunc_filepath: str
        Path to the average functional image to be used as reference in the last applywarp step.

    atlas2anat_nonlin_xfm_filepath: str
        Path to the atlas to anatomical brain linear transformation .mat file.
        If you have the inverse transformation, i.e., anatomical brain to atlas, set is_atlas2anat_inverted to True.

    is_atlas2anat_inverted: bool
        If False will have to calculate the inverse atlas2anat transformation to apply the transformations.
        This step will be performed with FSL invwarp.

    anat2func_lin_xfm_filepath: str
        Path to the anatomical to functional .mat linear transformation file.

    atlasinanat_out_filepath: str
        Path to output file which will contain the 3D atlas in the subject anatomical space.

    atlasinfunc_out_filepath: str
        Path to output file which will contain the 3D atlas in the subject functional space.

    verbose: bool
        If verbose will show DEBUG log info.

    rewrite: bool
        If True will re-run all the commands overwriting any existing file. Otherwise will check if
        each file exists and if it does won't run the command.

    parallel: bool
        If True will launch the commands using ${FSLDIR}/fsl_sub to use the cluster infrastructure you have setup
        with FSL (SGE or HTCondor).
    """
    if is_atlas2anat_inverted:
        # I already have the inverted fields I need
        anat_to_mni_nl_inv = atlas2anat_nonlin_xfm_filepath
    else:
        # I am creating the inverted fields then...need output file path:
        output_dir         = op.abspath   (op.dirname(atlasinanat_out_filepath))
        ext                = get_extension(atlas2anat_nonlin_xfm_filepath)
        anat_to_mni_nl_inv = op.join(output_dir, remove_ext(op.basename(atlas2anat_nonlin_xfm_filepath)) + '_inv' + ext)

    # setup the commands to be called
    invwarp_cmd   = op.join('${FSLDIR}', 'bin', 'invwarp')
    applywarp_cmd = op.join('${FSLDIR}', 'bin', 'applywarp')
    fslsub_cmd    = op.join('${FSLDIR}', 'bin', 'fsl_sub')

    # add fsl_sub before the commands
    if parallel:
        invwarp_cmd   = fslsub_cmd + ' ' + invwarp_cmd
        applywarp_cmd = fslsub_cmd + ' ' + applywarp_cmd

    # create the inverse fields
    if rewrite or (not is_atlas2anat_inverted and not op.exists(anat_to_mni_nl_inv)):
        log.debug('Creating {}.\n'.format(anat_to_mni_nl_inv))
        cmd  = invwarp_cmd + ' '
        cmd += '-w {} '.format(atlas2anat_nonlin_xfm_filepath)
        cmd += '-o {} '.format(anat_to_mni_nl_inv)
        cmd += '-r {} '.format(anatbrain_filepath)
        log.debug('Running {}'.format(cmd))
        check_call(cmd)

    # transform the atlas to anatomical space
    if rewrite or not op.exists(atlasinanat_out_filepath):
        log.debug('Creating {}.\n'.format(atlasinanat_out_filepath))
        cmd  = applywarp_cmd + ' '
        cmd += '--in={}     '.format(atlas_filepath)
        cmd += '--ref={}    '.format(anatbrain_filepath)
        cmd += '--warp={}   '.format(anat_to_mni_nl_inv)
        cmd += '--interp={} '.format(interp)
        cmd += '--out={}    '.format(atlasinanat_out_filepath)
        log.debug('Running {}'.format(cmd))
        check_call(cmd)

    # transform the atlas to functional space
    if rewrite or not op.exists(atlasinfunc_out_filepath):
        log.debug('Creating {}.\n'.format(atlasinfunc_out_filepath))
        cmd  = applywarp_cmd + ' '
        cmd += '--in={}     '.format(atlasinanat_out_filepath)
        cmd += '--ref={}    '.format(meanfunc_filepath)
        cmd += '--premat={} '.format(anat2func_lin_xfm_filepath)
        cmd += '--interp={} '.format(interp)
        cmd += '--out={}    '.format(atlasinfunc_out_filepath)
        log.debug('Running {}'.format(cmd))
        check_call(cmd)


