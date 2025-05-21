"""
Mapping between file operations and fsspec.

This module provides the core mapping functionality that redirects standard
file operations to fsspec operations.
"""

import os
import pathlib
from typing import Callable, Dict, Optional, Tuple, Union, Any

from .atomic import AtomicFileWrapper, AtomicTextIOWrapper
from .utils import create_fsspec_fs, create_path_mapper_from_dict


class FSSpecMapping:
    """
    Maps standard file operations to fsspec operations.

    This class provides the implementation of file operations that
    are redirected to an fsspec filesystem.
    """

    def __init__(
        self,
        fs,
        path_mapping=None,
        atomic_writes=True,
        atomic_suffix=".tmp",
        atomic_prefix=".",
    ):
        """
        Initialize the mapping between file operations and fsspec.

        Parameters
        ----------
        fs : fsspec.AbstractFileSystem
            The filesystem to use for operations
        path_mapping : callable, dict, or None
            Function that takes (path, operation_name) and returns (bool, mapped_path)
            Where the bool indicates if the operation should be patched and mapped_path
            is the new path to use if patched.
            If a dict, maps local paths to remote paths.
            If None, all paths are used as-is.
        atomic_writes : bool
            Whether to use atomic write operations
        atomic_suffix : str
            Suffix for temporary files in atomic writes
        atomic_prefix : str
            Prefix for temporary files in atomic writes
        """
        self.fs = fs
        self.atomic_writes = atomic_writes
        self.atomic_suffix = atomic_suffix
        self.atomic_prefix = atomic_prefix

        # Set up path mapping function
        if path_mapping is None:
            # No path mapping - operations on all paths as-is
            self._path_mapper = lambda path, operation: (
                (True, path) if path else (False, path)
            )
        elif isinstance(path_mapping, dict):
            # Dictionary mapping - use helper to create mapper
            self._path_mapper = create_path_mapper_from_dict(path_mapping)
        elif callable(path_mapping):
            # Callable - use directly
            self._path_mapper = path_mapping
        else:
            raise TypeError("path_mapping must be None, a dict, or a callable")

        # Extensions dictionary for custom implementations
        self._extensions = {}

    def map_path(self, path, operation="default"):
        """
        Check if a path should be patched and return the mapped path.

        Parameters
        ----------
        path : str or pathlib.Path
            The path being operated on
        operation : str
            The name of the operation being performed

        Returns
        -------
        tuple
            (should_patch, mapped_path) where:
            - should_patch (bool): True if the operation should be patched
            - mapped_path (str): The path to use if patched
        """
        # Convert path to string if it's a Path object
        if isinstance(path, pathlib.Path):
            path = str(path)

        # Ensure path is a string
        if not isinstance(path, str):
            return False, path

        return self._path_mapper(path, operation)

    def register_extension(self, operation_name, function):
        """
        Register a custom function to handle a specific operation.

        Parameters
        ----------
        operation_name : str
            The name of the operation to extend (e.g., 'open', 'os_mkdir')
        function : callable
            The function to call instead of the default implementation

        Returns
        -------
        None
        """
        self._extensions[operation_name] = function

    def __getattr__(self, name):
        """
        Get an attribute, checking for extensions first.

        Parameters
        ----------
        name : str
            The name of the attribute to get

        Returns
        -------
        The attribute value, or the extension function if registered

        Raises
        ------
        AttributeError
            If the attribute is not found
        """
        # Check for extension
        if name in self._extensions:
            return self._extensions[name]

        # If not found, raise AttributeError
        raise AttributeError(
            f"'{self.__class__.__name__}' object has no attribute '{name}'"
        )

    def context(
        self, patch_open=True, patch_os=True, patch_pathlib=True, patch_shutil=True
    ):
        """
        Create a context manager that patches file operations.

        Parameters
        ----------
        patch_open : bool, default True
            Whether to patch the built-in open function
        patch_os : bool, default True
            Whether to patch os module functions
        patch_pathlib : bool, default True
            Whether to patch pathlib.Path class
        patch_shutil : bool, default True
            Whether to patch shutil module functions

        Returns
        -------
        FSBridgeContext
            A context manager that patches file operations
        """
        from .core import FSBridgeContext

        return FSBridgeContext(
            self,
            patch_open=patch_open,
            patch_os=patch_os,
            patch_pathlib=patch_pathlib,
            patch_shutil=patch_shutil,
        )

    # File operations implementations

    def open(self, file, mode="r", *args, **kwargs):
        """
        Open a file on the fsspec filesystem.

        Parameters
        ----------
        file : str
            The file path to open
        mode : str
            The mode to open the file with
        *args, **kwargs
            Additional arguments to pass to fs.open

        Returns
        -------
        file-like object
            A file-like object for the requested file
        """
        should_patch, mapped_path = self.map_path(file, "open")
        if not should_patch:
            raise ValueError(f"Path {file} should not be patched")

        # Handle atomic writes if enabled
        if self.atomic_writes and "w" in mode and "b" not in mode:
            # For text mode with atomic writes, we need special handling
            return AtomicTextIOWrapper(
                self.fs,
                mapped_path,
                mode,
                suffix=self.atomic_suffix,
                prefix=self.atomic_prefix,
                *args,
                **kwargs,
            )
        elif self.atomic_writes and "w" in mode:
            # For binary mode with atomic writes
            return AtomicFileWrapper(
                self.fs,
                mapped_path,
                mode,
                suffix=self.atomic_suffix,
                prefix=self.atomic_prefix,
                *args,
                **kwargs,
            )

        # Normal open without atomic writes
        return self.fs.open(mapped_path, mode, *args, **kwargs)

    # os.path mappings
    def os_path_exists(self, path, *args, **kwargs):
        """Check if a path exists on the fsspec filesystem."""
        should_patch, mapped_path = self.map_path(path, "os.path.exists")
        if not should_patch:
            raise ValueError(f"Path {path} should not be patched")
        return self.fs.exists(mapped_path)

    def os_path_isdir(self, path, *args, **kwargs):
        """Check if a path is a directory on the fsspec filesystem."""
        should_patch, mapped_path = self.map_path(path, "os.path.isdir")
        if not should_patch:
            raise ValueError(f"Path {path} should not be patched")
        return self.fs.isdir(mapped_path)

    def os_path_isfile(self, path, *args, **kwargs):
        """Check if a path is a file on the fsspec filesystem."""
        should_patch, mapped_path = self.map_path(path, "os.path.isfile")
        if not should_patch:
            raise ValueError(f"Path {path} should not be patched")
        return self.fs.isfile(mapped_path)

    def os_path_getsize(self, path, *args, **kwargs):
        """Get the size of a file on the fsspec filesystem."""
        should_patch, mapped_path = self.map_path(path, "os.path.getsize")
        if not should_patch:
            raise ValueError(f"Path {path} should not be patched")
        return self.fs.info(mapped_path)["size"]

    def os_path_getmtime(self, path, *args, **kwargs):
        """Get the modification time of a file on the fsspec filesystem."""
        should_patch, mapped_path = self.map_path(path, "os.path.getmtime")
        if not should_patch:
            raise ValueError(f"Path {path} should not be patched")

        # Some fsspec filesystems don't provide mtime, handle that case
        info = self.fs.info(mapped_path)
        return info.get("mtime", info.get("modified", 0))

    def os_path_getctime(self, path, *args, **kwargs):
        """Get the creation time of a file on the fsspec filesystem."""
        should_patch, mapped_path = self.map_path(path, "os.path.getctime")
        if not should_patch:
            raise ValueError(f"Path {path} should not be patched")

        # Some fsspec filesystems don't provide ctime, handle that case
        info = self.fs.info(mapped_path)
        return info.get("ctime", info.get("created", 0))

    # os function mappings
    def os_mkdir(self, path, mode=0o777, *args, **kwargs):
        """Create a directory on the fsspec filesystem."""
        should_patch, mapped_path = self.map_path(path, "os.mkdir")
        if not should_patch:
            raise ValueError(f"Path {path} should not be patched")
        self.fs.mkdir(mapped_path)

    def os_makedirs(self, path, mode=0o777, exist_ok=False, *args, **kwargs):
        """Create directories recursively on the fsspec filesystem."""
        should_patch, mapped_path = self.map_path(path, "os.makedirs")
        if not should_patch:
            raise ValueError(f"Path {path} should not be patched")
        self.fs.makedirs(mapped_path, exist_ok=exist_ok)

    def os_listdir(self, path, *args, **kwargs):
        """List contents of a directory on the fsspec filesystem."""
        should_patch, mapped_path = self.map_path(path, "os.listdir")
        if not should_patch:
            raise ValueError(f"Path {path} should not be patched")

        files = self.fs.ls(mapped_path, detail=False)

        # Extract just the filenames (not full paths)
        return [os.path.basename(f) for f in files]

    def os_remove(self, path, *args, **kwargs):
        """Remove a file on the fsspec filesystem."""
        should_patch, mapped_path = self.map_path(path, "os.remove")
        if not should_patch:
            raise ValueError(f"Path {path} should not be patched")
        self.fs.rm(mapped_path)

    def os_unlink(self, path, *args, **kwargs):
        """Remove a file on the fsspec filesystem (alias for remove)."""
        should_patch, mapped_path = self.map_path(path, "os.unlink")
        if not should_patch:
            raise ValueError(f"Path {path} should not be patched")
        self.fs.rm(mapped_path)

    def os_rmdir(self, path, *args, **kwargs):
        """Remove an empty directory on the fsspec filesystem."""
        should_patch, mapped_path = self.map_path(path, "os.rmdir")
        if not should_patch:
            raise ValueError(f"Path {path} should not be patched")
        self.fs.rmdir(mapped_path)

    def os_rename(self, src, dst, *args, **kwargs):
        """Rename a file or directory on the fsspec filesystem."""
        should_patch_src, mapped_src = self.map_path(src, "os.rename.src")
        should_patch_dst, mapped_dst = self.map_path(dst, "os.rename.dst")

        if not should_patch_src or not should_patch_dst:
            raise ValueError(f"Paths should both be patched: {src} -> {dst}")

        self.fs.mv(mapped_src, mapped_dst)

    # pathlib mappings
    def pathlib_exists(self, path, *args, **kwargs):
        """Check if a path exists (pathlib method)."""
        should_patch, mapped_path = self.map_path(path, "pathlib.exists")
        if not should_patch:
            raise ValueError(f"Path {path} should not be patched")
        return self.fs.exists(mapped_path)

    def pathlib_is_dir(self, path, *args, **kwargs):
        """Check if a path is a directory (pathlib method)."""
        should_patch, mapped_path = self.map_path(path, "pathlib.is_dir")
        if not should_patch:
            raise ValueError(f"Path {path} should not be patched")
        return self.fs.isdir(mapped_path)

    def pathlib_is_file(self, path, *args, **kwargs):
        """Check if a path is a file (pathlib method)."""
        should_patch, mapped_path = self.map_path(path, "pathlib.is_file")
        if not should_patch:
            raise ValueError(f"Path {path} should not be patched")
        return self.fs.isfile(mapped_path)

    def pathlib_stat(self, path, *args, **kwargs):
        """Get stat information (pathlib method)."""
        should_patch, mapped_path = self.map_path(path, "pathlib.stat")
        if not should_patch:
            raise ValueError(f"Path {path} should not be patched")

        # Create a simple stat_result-like object with values from info
        info = self.fs.info(mapped_path)

        class StatResult:
            def __init__(self, info):
                self.info = info
                self.st_size = info.get("size", 0)
                self.st_mtime = info.get("mtime", info.get("modified", 0))
                self.st_ctime = info.get("ctime", info.get("created", 0))
                self.st_mode = 0o777 if info.get("type") == "directory" else 0o666

        return StatResult(info)

    def pathlib_mkdir(
        self, path, mode=0o777, parents=False, exist_ok=False, *args, **kwargs
    ):
        """Create a directory (pathlib method)."""
        should_patch, mapped_path = self.map_path(path, "pathlib.mkdir")
        if not should_patch:
            raise ValueError(f"Path {path} should not be patched")

        if parents:
            return self.fs.makedirs(mapped_path, exist_ok=exist_ok)
        else:
            try:
                return self.fs.mkdir(mapped_path)
            except FileExistsError:
                if exist_ok:
                    return
                raise

    # shutil mappings
    def shutil_copy(self, src, dst, src_patch, dst_patch, *args, **kwargs):
        """Copy a file."""
        # Map paths if they should be patched
        src_path = self.map_path(src, "shutil.copy.src")[1] if src_patch else src
        dst_path = self.map_path(dst, "shutil.copy.dst")[1] if dst_patch else dst

        if src_patch and dst_patch:
            # Both paths are on the fsspec filesystem
            self.fs.copy(src_path, dst_path)
        elif src_patch:
            # Source is on fsspec, destination is on local filesystem
            with self.fs.open(src_path, "rb") as fsrc:
                with open(dst, "wb") as fdst:
                    while True:
                        chunk = fsrc.read(1024 * 1024)  # 1MB chunks
                        if not chunk:
                            break
                        fdst.write(chunk)
        elif dst_patch:
            # Source is on local filesystem, destination is on fsspec
            with open(src, "rb") as fsrc:
                with self.fs.open(dst_path, "wb") as fdst:
                    while True:
                        chunk = fsrc.read(1024 * 1024)  # 1MB chunks
                        if not chunk:
                            break
                        fdst.write(chunk)

    def shutil_copy2(self, src, dst, src_patch, dst_patch, *args, **kwargs):
        """Copy a file with metadata."""
        # In fsspec, we may not be able to preserve all metadata, but we do our best
        self.shutil_copy(src, dst, src_patch, dst_patch, *args, **kwargs)

    def shutil_copyfile(self, src, dst, src_patch, dst_patch, *args, **kwargs):
        """Copy file contents."""
        # This is essentially the same as copy for us
        self.shutil_copy(src, dst, src_patch, dst_patch, *args, **kwargs)

    def shutil_copytree(self, src, dst, src_patch, dst_patch, *args, **kwargs):
        """Copy a directory tree."""
        symlinks = kwargs.get("symlinks", False)
        ignore = kwargs.get("ignore", None)
        dirs_exist_ok = kwargs.get("dirs_exist_ok", False)

        # Map paths if they should be patched
        src_path = self.map_path(src, "shutil.copytree.src")[1] if src_patch else src
        dst_path = self.map_path(dst, "shutil.copytree.dst")[1] if dst_patch else dst

        # Create the destination directory
        if dst_patch:
            self.fs.makedirs(dst_path, exist_ok=dirs_exist_ok)
        else:
            os.makedirs(dst, exist_ok=dirs_exist_ok)

        # Get the list of files and directories to copy
        if src_patch:
            entries = self.fs.find(src_path, detail=True)
            files = [entry for entry in entries.values() if entry["type"] == "file"]
            relative_files = [os.path.relpath(file["name"], src_path) for file in files]
        else:
            relative_files = []
            for dirpath, dirnames, filenames in os.walk(src):
                for filename in filenames:
                    full_path = os.path.join(dirpath, filename)
                    relative_files.append(os.path.relpath(full_path, src))

        # Copy each file
        for relative_file in relative_files:
            src_file = (
                os.path.join(src, relative_file)
                if not src_patch
                else os.path.join(src_path, relative_file)
            )
            dst_file = (
                os.path.join(dst, relative_file)
                if not dst_patch
                else os.path.join(dst_path, relative_file)
            )

            # Create parent directories if needed
            dst_dir = os.path.dirname(dst_file)
            if dst_patch:
                self.fs.makedirs(dst_dir, exist_ok=True)
            else:
                os.makedirs(dst_dir, exist_ok=True)

            # Copy the file
            self.shutil_copy2(src_file, dst_file, src_patch, dst_patch)

        return dst

    def shutil_move(self, src, dst, src_patch, dst_patch, *args, **kwargs):
        """Move a file or directory."""
        if src_patch and dst_patch:
            # Both paths are on the fsspec filesystem
            # Map paths if they should be patched
            src_path = self.map_path(src, "shutil.move.src")[1]
            dst_path = self.map_path(dst, "shutil.move.dst")[1]
            self.fs.mv(src_path, dst_path)
        else:
            # Copy and then delete
            self.shutil_copy2(src, dst, src_patch, dst_patch, *args, **kwargs)
            if src_patch:
                src_path = self.map_path(src, "shutil.move.src")[1]
                self.fs.rm(src_path)
            else:
                if os.path.isdir(src):
                    import shutil

                    shutil.rmtree(src)
                else:
                    os.remove(src)

    def shutil_rmtree(self, path, src_patch, dst_patch, *args, **kwargs):
        """Remove a directory tree."""
        # We only care about the first path for rmtree
        if src_patch:
            path_mapped = self.map_path(path, "shutil.rmtree")[1]
            self.fs.rm(path_mapped, recursive=True)
        else:
            import shutil

            shutil.rmtree(path, *args, **kwargs)


def create_fs_mapping(
    fs=None,
    path_mapping=None,
    atomic_writes=True,
    atomic_suffix=".tmp",
    atomic_prefix=".",
    **fs_kwargs,
):
    """
    Create a mapping between standard file operations and an fsspec filesystem.

    Parameters
    ----------
    fs : fsspec.AbstractFileSystem or str, optional
        The filesystem to use or a string representing the filesystem type.
        If None, a local filesystem is created.
    path_mapping : callable, dict, or None
        Function that takes (path, operation) and returns (should_patch, mapped_path).
        If a dict, maps local paths to remote paths.
        If None, all operations are redirected.
    atomic_writes : bool, default True
        Whether to use atomic write operations
    atomic_suffix : str, default ".tmp"
        Suffix for temporary files in atomic writes
    atomic_prefix : str, default "."
        Prefix for temporary files in atomic writes
    **fs_kwargs : dict
        Additional keyword arguments to pass to the filesystem constructor if fs is a string

    Returns
    -------
    FSSpecMapping
        The mapping object
    """
    # Create filesystem if needed
    if fs is None:
        fs = create_fsspec_fs("file")
    elif isinstance(fs, str):
        fs = create_fsspec_fs(fs, **fs_kwargs)

    # Create the mapping
    return FSSpecMapping(
        fs,
        path_mapping=path_mapping,
        atomic_writes=atomic_writes,
        atomic_suffix=atomic_suffix,
        atomic_prefix=atomic_prefix,
    )
