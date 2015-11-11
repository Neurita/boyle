
from .utils.logger import setup_logging

setup_logging()

# Boolean controlling whether the joblib caches should be
# flushed if the version of certain modules changes (eg nibabel, as it
# does not respect the backward compatibility in some of its internal
# structures
# This  is used in boyle.utils.cache_mixin
CHECK_CACHE_VERSION = True
