"""
fsbridge: Transparent redirection of Python file operations to fsspec backends
=============================================================================

A pragmatic monkey-patching library that transparently redirects Python's standard
file operations to FSSpec backends, allowing existing code to work with any filesystem
without modification.
"""

from .core import fsbridge_context, FSBridgeContext
from .mapping import FSSpecMapping, create_fs_mapping
from .utils import create_fsspec_fs, create_path_mapper_from_dict

__version__ = "0.1.0"

__all__ = [
    "fsbridge_context",
    "FSBridgeContext",
    "FSSpecMapping",
    "create_fs_mapping",
    "create_fsspec_fs",
    "create_path_mapper_from_dict",
]
