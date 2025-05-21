"""
Core functionality for fsbridge package.

This module provides the context manager that handles patching
of Python's file-related operations.
"""

import builtins
import os
import pathlib
import shutil
import functools
from contextlib import contextmanager

from .mapping import FSSpecMapping, create_fs_mapping


class FSBridgeContext:
    """
    Context manager for patching file system operations to redirect them to fsspec backends.

    This class temporarily replaces standard Python file operations with versions that
    redirect to a specified fsspec filesystem when paths match certain criteria.
    """

    def __init__(
        self,
        fs_mapping,
        patch_open=True,
        patch_os=True,
        patch_pathlib=True,
        patch_shutil=True,
    ):
        """
        Initialize an FSBridge context.

        Parameters
        ----------
        fs_mapping : FSSpecMapping
            The mapping object that implements file operations
        patch_open : bool, default True
            Whether to patch the built-in open function
        patch_os : bool, default True
            Whether to patch os module functions
        patch_pathlib : bool, default True
            Whether to patch pathlib.Path class
        patch_shutil : bool, default True
            Whether to patch shutil module functions
        """
        self.fs_mapping = fs_mapping

        # Configure which operations to patch
        self.patch_open = patch_open
        self.patch_os = patch_os
        self.patch_pathlib = patch_pathlib
        self.patch_shutil = patch_shutil

        # Keep track of original functions
        self._originals = {}

    def __enter__(self):
        """Enter the context manager, patching file operations."""
        self._patch_operations()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager, restoring original file operations."""
        self._restore_operations()

    def _patch_operations(self):
        """Patch the file operations based on configuration."""
        if self.patch_open:
            self._patch_open()

        if self.patch_os:
            self._patch_os_functions()

        if self.patch_pathlib:
            self._patch_pathlib()

        if self.patch_shutil:
            self._patch_shutil()

    def _restore_operations(self):
        """Restore all original functions."""
        for target, attr_name, original in self._originals.values():
            setattr(target, attr_name, original)
        self._originals = {}

    def _patch_function(self, target, attr_name, replacement):
        """
        Patch a function with its replacement.

        Parameters
        ----------
        target : module or class
            The object that contains the function to patch
        attr_name : str
            The name of the attribute to patch
        replacement : callable
            The replacement function
        """
        original = getattr(target, attr_name)
        self._originals[(id(target), attr_name)] = (target, attr_name, original)
        setattr(target, attr_name, replacement)

    def _patch_open(self):
        """Patch the built-in open function."""
        original_open = builtins.open
        fs_mapping = self.fs_mapping

        @functools.wraps(original_open)
        def patched_open(file, mode="r", *args, **kwargs):
            # Check if we should redirect this open call
            if isinstance(file, str):
                should_patch, _ = fs_mapping.map_path(file, "open")
                if should_patch:
                    return fs_mapping.open(file, mode, *args, **kwargs)
            return original_open(file, mode, *args, **kwargs)

        self._patch_function(builtins, "open", patched_open)

    def _patch_os_functions(self):
        """Patch relevant functions in the os module."""
        fs_mapping = self.fs_mapping

        # os.path functions
        for func_name in [
            "exists",
            "isdir",
            "isfile",
            "getsize",
            "getmtime",
            "getctime",
        ]:
            original_func = getattr(os.path, func_name)

            @functools.wraps(original_func)
            def patched_func(path, *args, func_name=func_name, **kwargs):
                should_patch, _ = fs_mapping.map_path(path, f"os.path.{func_name}")
                if should_patch:
                    return getattr(fs_mapping, f"os_path_{func_name}")(
                        path, *args, **kwargs
                    )
                return original_func(path, *args, **kwargs)

            self._patch_function(os.path, func_name, patched_func)

        # os functions
        for func_name in [
            "mkdir",
            "makedirs",
            "listdir",
            "remove",
            "unlink",
            "rmdir",
            "rename",
        ]:
            if hasattr(os, func_name):
                original_func = getattr(os, func_name)

                if func_name == "rename":
                    # Special handling for rename which takes two paths
                    @functools.wraps(original_func)
                    def patched_rename(src, dst, *args, **kwargs):
                        should_patch_src, _ = fs_mapping.map_path(src, "os.rename.src")
                        should_patch_dst, _ = fs_mapping.map_path(dst, "os.rename.dst")

                        if should_patch_src and should_patch_dst:
                            return fs_mapping.os_rename(src, dst, *args, **kwargs)
                        return original_func(src, dst, *args, **kwargs)

                    self._patch_function(os, func_name, patched_rename)
                else:

                    @functools.wraps(original_func)
                    def patched_func(path, *args, func_name=func_name, **kwargs):
                        should_patch, _ = fs_mapping.map_path(path, f"os.{func_name}")
                        if should_patch:
                            return getattr(fs_mapping, f"os_{func_name}")(
                                path, *args, **kwargs
                            )
                        return original_func(path, *args, **kwargs)

                    self._patch_function(os, func_name, patched_func)

    def _patch_pathlib(self):
        """Patch relevant methods in pathlib.Path."""
        fs_mapping = self.fs_mapping

        # Methods that take no arguments beyond self
        for method_name in ["exists", "is_dir", "is_file", "stat", "mkdir"]:
            original_method = getattr(pathlib.Path, method_name)

            @functools.wraps(original_method)
            def patched_method(self_path, *args, method_name=method_name, **kwargs):
                path_str = str(self_path)
                should_patch, _ = fs_mapping.map_path(
                    path_str, f"pathlib.{method_name}"
                )
                if should_patch:
                    return getattr(fs_mapping, f"pathlib_{method_name}")(
                        path_str, *args, **kwargs
                    )
                return original_method(self_path, *args, **kwargs)

            self._patch_function(pathlib.Path, method_name, patched_method)

        # Path.open method needs special handling
        original_path_open = pathlib.Path.open

        @functools.wraps(original_path_open)
        def patched_path_open(self_path, mode="r", *args, **kwargs):
            path_str = str(self_path)
            should_patch, _ = fs_mapping.map_path(path_str, "pathlib.open")
            if should_patch:
                return fs_mapping.open(path_str, mode, *args, **kwargs)
            return original_path_open(self_path, mode, *args, **kwargs)

        self._patch_function(pathlib.Path, "open", patched_path_open)

    def _patch_shutil(self):
        """Patch relevant functions in the shutil module."""
        fs_mapping = self.fs_mapping

        for func_name in ["copy", "copy2", "copyfile", "copytree", "move", "rmtree"]:
            original_func = getattr(shutil, func_name)

            if func_name == "rmtree":
                # rmtree takes only one path
                @functools.wraps(original_func)
                def patched_rmtree(path, *args, **kwargs):
                    should_patch, _ = fs_mapping.map_path(path, f"shutil.{func_name}")
                    if should_patch:
                        return fs_mapping.shutil_rmtree(
                            path, should_patch, False, *args, **kwargs
                        )
                    return original_func(path, *args, **kwargs)

                self._patch_function(shutil, func_name, patched_rmtree)
            else:
                # These functions take two paths
                @functools.wraps(original_func)
                def patched_func(src, dst, *args, func_name=func_name, **kwargs):
                    should_patch_src, _ = fs_mapping.map_path(
                        src, f"shutil.{func_name}.src"
                    )
                    should_patch_dst, _ = fs_mapping.map_path(
                        dst, f"shutil.{func_name}.dst"
                    )

                    if should_patch_src or should_patch_dst:
                        return getattr(fs_mapping, f"shutil_{func_name}")(
                            src,
                            dst,
                            should_patch_src,
                            should_patch_dst,
                            *args,
                            **kwargs,
                        )
                    return original_func(src, dst, *args, **kwargs)

                self._patch_function(shutil, func_name, patched_func)


@contextmanager
def fsbridge_context(
    fs=None,
    path_mapping=None,
    atomic_writes=True,
    atomic_suffix=".tmp",
    atomic_prefix=".",
    patch_open=True,
    patch_os=True,
    patch_pathlib=True,
    patch_shutil=True,
    **fs_kwargs,
):
    """
    Context manager that patches file operations to redirect them to fsspec.

    Parameters
    ----------
    fs : fsspec.AbstractFileSystem, FSSpecMapping, or str, optional
        The filesystem to use, a FSSpecMapping instance, or a string with the filesystem type.
        If None, a local filesystem is created.
    path_mapping : callable, dict, or None
        Function that takes (path, operation) and returns (should_patch, mapped_path).
        If a dict, maps local paths to remote paths.
        If None, all operations are redirected.
        Ignored if fs is an FSSpecMapping instance.
    atomic_writes : bool, default True
        Whether to perform atomic write operations using temporary files.
        Ignored if fs is an FSSpecMapping instance.
    atomic_suffix : str, default ".tmp"
        Suffix to use for temporary files during atomic writes.
        Ignored if fs is an FSSpecMapping instance.
    atomic_prefix : str, default "."
        Prefix to use for temporary files during atomic writes.
        Ignored if fs is an FSSpecMapping instance.
    patch_open : bool, default True
        Whether to patch the built-in open function.
    patch_os : bool, default True
        Whether to patch os module functions.
    patch_pathlib : bool, default True
        Whether to patch pathlib.Path class.
    patch_shutil : bool, default True
        Whether to patch shutil module functions.
    **fs_kwargs : dict
        Additional keyword arguments to pass to the filesystem constructor if fs is a string.
        Ignored if fs is an FSSpecMapping instance.

    Yields
    ------
    FSBridgeContext
        The context manager instance

    Examples
    --------
    >>> # Map paths with a dictionary
    >>> with fsbridge_context(path_mapping={'/outputs/': '/tmp/actual_outputs/'}):
    ...     with open('/outputs/results.csv', 'w') as f:
    ...         f.write('data,value\\n1,2\\n')

    >>> # Custom path mapper function
    >>> def my_path_mapper(path, operation):
    ...     if path.endswith('.csv'):
    ...         return True, f"/special/csv/{os.path.basename(path)}"
    ...     return False, path
    >>>
    >>> with fsbridge_context(path_mapping=my_path_mapper):
    ...     with open('data.csv', 'w') as f:  # This will be patched
    ...         f.write('data,value\\n1,2\\n')
    """
    # Create fs_mapping if needed
    if isinstance(fs, FSSpecMapping):
        fs_mapping = fs
    else:
        fs_mapping = create_fs_mapping(
            fs=fs,
            path_mapping=path_mapping,
            atomic_writes=atomic_writes,
            atomic_suffix=atomic_suffix,
            atomic_prefix=atomic_prefix,
            **fs_kwargs,
        )

    # Create the context manager
    context = FSBridgeContext(
        fs_mapping,
        patch_open=patch_open,
        patch_os=patch_os,
        patch_pathlib=patch_pathlib,
        patch_shutil=patch_shutil,
    )

    # Enter the context
    try:
        context.__enter__()
        yield context
    finally:
        context.__exit__(None, None, None)
