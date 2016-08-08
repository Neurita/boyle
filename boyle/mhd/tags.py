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


import numpy as np

# the order of these tags matter
MHD_TAGS = ['ObjectType',
            'NDims',
            'BinaryData',
            'BinaryDataByteOrderMSB',
            'CompressedData',
            'CompressedDataSize',
            'TransformMatrix',
            'Offset',
            'CenterOfRotation',
            'AnatomicalOrientation',
            'ElementSpacing',
            'DimSize',
            'ElementType',
            'ElementDataFile',
            'Comment',
            'SeriesDescription',
            'AcquisitionDate',
            'AcquisitionTime',
            'StudyDate',
            'StudyTime']


MHD_TO_NUMPY_TYPE   = {'MET_UCHAR' : np.uint8,
                       'MET_CHAR'  : np.int8,
                       'MET_USHORT': np.uint8,
                       'MET_SHORT' : np.int8,
                       'MET_UINT'  : np.uint32,
                       'MET_INT'   : np.int32,
                       'MET_ULONG' : np.uint64,
                       'MET_LONG'  : np.int64,
                       'MET_FLOAT' : np.float32,
                       'MET_DOUBLE': np.float64}


NDARRAY_TO_ARRAY_TYPE = {np.float  : 'f',
                         np.uint8  : 'H',
                         np.int8   : 'h',
                         np.uint16 : 'I',
                         np.int16  : 'i',
                         np.uint32 : 'I',
                         np.int32  : 'i',
                         np.uint64 : 'I',
                         np.int64  : 'i',
                         np.float32: 'f',
                         np.float64: 'd',}


NUMPY_TO_MHD_TYPE = {v: k for k, v in MHD_TO_NUMPY_TYPE.items()}
# ARRAY_TO_NDARRAY_TYPE = {v: k for k, v in NDARRAY_TO_ARRAY_TYPE.items()}
