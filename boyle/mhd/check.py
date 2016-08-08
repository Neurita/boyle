# coding=utf-8
# -------------------------------------------------------------------------------
# Author: Alexandre Manhaes Savio <alexsavio@gmail.com>
# Author: Oier Echaniz
# Grupo de Inteligencia Computational <www.ehu.es/ccwintco>
# Universidad del Pais Vasco UPV/EHU
#
# 2015, Alexandre Manhaes Savio
# Use this at your own risk!
# -------------------------------------------------------------------------------

import warnings
import os.path          as      op
from   six              import  string_types

from   .read            import  load_raw_data_with_mhd
from   ..nifti.check    import  is_img

from   ..files.names    import  get_extension
from   ..exceptions     import  FileNotFound


def check_mhd_img(image, make_it_3d=False):
    """Check that image is a proper img. Turn filenames into objects.

    Parameters
    ----------
    image: img-like object or str
        Can either be:
        - a file path to a .mhd file. (if it is a .raw file, this won't work).
        - any object with get_data() and get_affine() methods, e.g., nibabel.Nifti1Image.
        If niimg is a string, consider it as a path to .mhd image and
        call load_raw_data_with_mhd on it. If it is an object, check if get_data()
        and get_affine() methods are present, raise TypeError otherwise.

    make_it_3d: boolean, optional
        If True, check if the image is a 3D image and raise an error if not.

    Returns
    -------
    result: nifti-like
       result can be nibabel.Nifti1Image or the input, as-is. It is guaranteed
       that the returned object has get_data() and get_affine() methods.
    """
    if isinstance(image, string_types):
        # a filename, load it
        if not op.exists(image):
            raise FileNotFound(image)

        ext = get_extension(image).lower()
        if not 'mhd' in ext:
            warnings.warn('Expecting a filepath with `.mhd` extension, got {}.'.format(image))

        img, hdr = load_raw_data_with_mhd(image)
        if make_it_3d:
            img = _make_it_3d(img)

        return img

    elif is_img(image):
        return image

    else:
        raise TypeError('Data given cannot be converted to a nifti'
                        ' image: this object -"{}"- does not have'
                        ' get_data or get_affine methods'.format(type(image)))


def _make_it_3d(img):
    """Enforce that img is a 3D img-like object, if it is not, raise a TypeError.
    i.e., remove dimensions of size 1.

    Parameters
    ----------
    img: numpy.ndarray
        Image data array

    Returns
    -------
    3D numpy ndarray object
    """
    shape = img.shape

    if len(shape) == 3:
        return img

    elif len(shape) == 4 and shape[3] == 1:
        # "squeeze" the image.
        return img[:, :, :, 0]

    else:
        raise TypeError('A 3D image is expected, but an image with a shape of {} was given.'.format(shape))
