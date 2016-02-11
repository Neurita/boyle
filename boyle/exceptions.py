"""
Extended exceptions
"""


from .utils.compat import _basestring


def compose_err_msg(msg, **kwargs):
    """Append key-value pairs to msg, for display.

    Parameters
    ----------
    msg: string
        arbitrary message
    kwargs: dict
        arbitrary dictionary

    Returns
    -------
    updated_msg: string
        msg, with "key: value" appended. Only string values are appended.

    Example
    -------
    >>> compose_err_msg('Error message with arguments...', arg_num=123, \
        arg_str='filename.nii', arg_bool=True)
    'Error message with arguments...\\narg_str: filename.nii'
    >>>
    """
    updated_msg = msg
    for k, v in sorted(kwargs.items()):
        if isinstance(v, _basestring):  # print only str-like arguments
            updated_msg += "\n" + k + ": " + v

    return updated_msg


class FilesNotCompatible(Exception):
    file_types = 'files'

    def __init__(self, file_path1, file_path2, message=None):
        msg = '{} {} and {} are not compatible.'.format(self.file_types.capitalize(),
                                                        file_path1,
                                                        file_path2)
        if message is not None:
            msg += '. ' + message

        Exception.__init__(self, msg)


class NiftiFilesNotCompatible(FilesNotCompatible):
    file_types = 'nifti files'


class PathNotFoundError(Exception):
    path_type = 'path'

    def __init__(self, file_path, message=None):

        msg = 'Could not find {0} {1}.'.format(self.path_type,
                                               file_path)
        if message is not None:
            msg += '. ' + message

        Exception.__init__(self, msg)


class PathAlreadyExists(Exception):
    path_type = 'path'

    def __init__(self, file_path, message=None):

        msg = '{0} {1} already exists {1}.'.format(self.path_type.capitalize(),
                                                   file_path)
        if message is not None:
            msg += '. ' + message

        Exception.__init__(self, msg)


class FileNotFound(PathNotFoundError):
    path_type = 'file'


class FolderNotFound(PathNotFoundError):
    path_type = 'folder'


class FileAlreadyExists(PathAlreadyExists):
    path_type = 'file'


class FolderAlreadyExists(PathAlreadyExists):
    path_type = 'folder'
