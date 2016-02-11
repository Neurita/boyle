# coding=utf-8
"""
Utilities to manage volume files
"""
#------------------------------------------------------------------------------
# Author: Alexandre Manhaes Savio <alexsavio@gmail.com>
# Nuklear Medizin Department
# Klinikum rechts der Isar der Technische Universitaet Muenchen, Deutschland
#
# 2015, Alexandre Manhaes Savio
# Use this at your own risk!
#------------------------------------------------------------------------------

import numpy as np

from .check import check_img_compatibility, check_img


def merge_images(images, axis='t'):
    """ Concatenate `images` in the direction determined in `axis`.

    Parameters
    ----------
    images: list of str or img-like object.
        See NeuroImage constructor docstring.

    axis: str
      't' : concatenate images in time
      'x' : concatenate images in the x direction
      'y' : concatenate images in the y direction
      'z' : concatenate images in the z direction

    Returns
    -------
    merged: img-like object
    """
    # check if images is not empty
    if not images:
        return None

    # the given axis name to axis idx
    axis_dim = {'x': 0,
                'y': 1,
                'z': 2,
                't': 3,
                }

    # check if the given axis name is valid
    if axis not in axis_dim:
        raise ValueError('Expected `axis` to be one of ({}), got {}.'.format(set(axis_dim.keys()), axis))

    # check if all images are compatible with each other
    img1 = images[0]
    for img in images:
        check_img_compatibility(img1, img)

    # read the data of all the given images
    # TODO: optimize memory consumption by merging one by one.
    image_data = []
    for img in images:
        image_data.append(check_img(img).get_data())

    # if the work_axis is bigger than the number of axis of the images,
    # create a new axis for the images
    work_axis = axis_dim[axis]
    ndim = image_data[0].ndim
    if ndim - 1 < work_axis:
        image_data = [np.expand_dims(img, axis=work_axis) for img in image_data]

    # concatenate and return
    return np.concatenate(image_data, axis=work_axis)
