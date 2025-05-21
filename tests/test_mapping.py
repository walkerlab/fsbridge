"""
Tests for the FSSpecMapping class.
"""

import os
import pytest

from fsbridge.mapping import FSSpecMapping, create_fs_mapping
from fsbridge.utils import create_path_mapper_from_dict


def test_map_path(fs_mapping, temp_dir):
    """Test the map_path method."""
    # Test a path that should be mapped
    should_patch, mapped_path = fs_mapping.map_path("/test/file.txt", "open")
    assert should_patch
    assert mapped_path == os.path.join(temp_dir, "file.txt")

    # Test a path that should not be mapped
    should_patch, mapped_path = fs_mapping.map_path("/other/file.txt", "open")
    assert not should_patch
    assert mapped_path == "/other/file.txt"


def test_register_extension(fs_mapping, temp_dir):
    """Test registering an extension."""

    # Define a custom implementation
    def custom_open(self, file, mode="r", *args, **kwargs):
        should_patch, mapped_path = self.map_path(file, "custom_open")
        if not should_patch:
            raise ValueError(f"Path {file} should not be patched")
        return f"Custom open: {mapped_path} (mode: {mode})"

    # Register the extension
    fs_mapping.register_extension("custom_open", custom_open)

    # Use the extension
    result = fs_mapping.custom_open("/test/file.txt", "w")
    assert result == f"Custom open: {os.path.join(temp_dir, 'file.txt')} (mode: w)"


def test_create_fs_mapping_with_dict(fs, temp_dir):
    """Test creating a mapping with a dictionary."""
    # Create a mapping with a dictionary
    mapping = create_fs_mapping(fs=fs, path_mapping={"/test/": temp_dir})

    # Test mapping a path
    should_patch, mapped_path = mapping.map_path("/test/file.txt", "open")
    assert should_patch
    assert mapped_path == os.path.join(temp_dir, "file.txt")


def test_create_fs_mapping_with_callable(fs, path_mapper, temp_dir):
    """Test creating a mapping with a callable."""
    # Create a mapping with a callable
    mapping = create_fs_mapping(fs=fs, path_mapping=path_mapper)

    # Test mapping a path
    should_patch, mapped_path = mapping.map_path("/test/file.txt", "open")
    assert should_patch
    assert mapped_path == os.path.join(temp_dir, "file.txt")


def test_path_mapper_from_dict(temp_dir):
    """Test creating a path mapper from a dictionary."""
    # Create a path mapper
    mapper = create_path_mapper_from_dict({"/test/": temp_dir})

    # Test mapping a path
    should_patch, mapped_path = mapper("/test/file.txt", "open")
    assert should_patch
    assert mapped_path == os.path.join(temp_dir, "file.txt")

    # Test mapping a path that doesn't match
    should_patch, mapped_path = mapper("/other/file.txt", "open")
    assert not should_patch
    assert mapped_path == "/other/file.txt"


def test_operation_aware_mapping(fs, temp_dir):
    """Test operation-aware mapping."""

    # Create a path mapper that handles different operations
    def operation_mapper(path, operation):
        if not isinstance(path, str):
            return False, path

        if path.startswith("/test/") and "write" in operation:
            # Map write operations to 'writes' subdirectory
            mapped_path = os.path.join(temp_dir, "writes", path[6:])
            return True, mapped_path
        elif path.startswith("/test/") and "read" in operation:
            # Map read operations to 'reads' subdirectory
            mapped_path = os.path.join(temp_dir, "reads", path[6:])
            return True, mapped_path

        return False, path

    mapping = create_fs_mapping(fs=fs, path_mapping=operation_mapper)

    # Test write operation
    should_patch, mapped_path = mapping.map_path("/test/file.txt", "write")
    assert should_patch
    assert mapped_path == os.path.join(temp_dir, "writes", "file.txt")

    # Test read operation
    should_patch, mapped_path = mapping.map_path("/test/file.txt", "read")
    assert should_patch
    assert mapped_path == os.path.join(temp_dir, "reads", "file.txt")
