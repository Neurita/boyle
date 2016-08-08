"""
Helper functions to import external things.
"""


def import_pyfile(filepath, mod_name=None):
    """
    Imports the contents of filepath as a Python module.

    :param filepath: string

    :param mod_name: string
    Name of the module when imported

    :return: module
    Imported module
    """
    import sys
    if sys.version_info.major == 3:
        import importlib.machinery
        loader = importlib.machinery.SourceFileLoader('', filepath)
        mod = loader.load_module(mod_name)
    else:
        import imp
        mod = imp.load_source(mod_name, filepath)

    return mod
