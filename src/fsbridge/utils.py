"""
Utility functions for fsbridge.

This module provides helper functions for creating filesystems
and path mappers.
"""

import os
from typing import Dict, Callable, Tuple


def create_fsspec_fs(fs_type="file", **fs_kwargs):
    """
    Create an fsspec filesystem.

    Parameters
    ----------
    fs_type : str, default "file"
        The fsspec filesystem type to create
    **fs_kwargs : dict
        Additional keyword arguments to pass to the filesystem constructor

    Returns
    -------
    fsspec.AbstractFileSystem
        The created filesystem
    """
    import fsspec

    return fsspec.filesystem(fs_type, **fs_kwargs)


def create_path_mapper_from_dict(
    path_mapping: Dict[str, str],
) -> Callable[[str, str], Tuple[bool, str]]:
    """
    Create a path mapper function from a dictionary.

    Parameters
    ----------
    path_mapping : dict
        Dictionary mapping local paths to remote paths

    Returns
    -------
    callable
        A function that takes (path, operation) and returns (should_patch, mapped_path)
    """

    def mapper(path, operation):
        if not path:
            return False, path

        for local_path, remote_path in path_mapping.items():
            if path.startswith(local_path):
                # Replace local path prefix with remote path
                rel_path = path[len(local_path) :].lstrip("/")
                if remote_path:
                    mapped_path = f"{remote_path.rstrip('/')}/{rel_path}"
                else:
                    mapped_path = rel_path
                return True, mapped_path
        return False, path

    return mapper
