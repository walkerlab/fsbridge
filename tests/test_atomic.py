"""
Tests for atomic file operations.
"""

import os
import pytest

from fsbridge.atomic import AtomicFileWrapper, AtomicTextIOWrapper


def test_atomic_binary(fs, temp_dir):
    """Test atomic binary file operations."""
    test_path = os.path.join(temp_dir, "test.bin")
    test_data = b"Hello, binary world!"

    # Write data
    with AtomicFileWrapper(fs, test_path, "wb") as f:
        f.write(test_data)

    # Check the file exists and has the right content
    assert os.path.exists(test_path)

    with open(test_path, "rb") as f:
        content = f.read()

    assert content == test_data


def test_atomic_text(fs, temp_dir):
    """Test atomic text file operations."""
    test_path = os.path.join(temp_dir, "test.txt")
    test_data = "Hello, text world!"

    # Write data
    with AtomicTextIOWrapper(fs, test_path, "w") as f:
        f.write(test_data)

    # Check the file exists and has the right content
    assert os.path.exists(test_path)

    with open(test_path, "r") as f:
        content = f.read()

    assert content == test_data


def test_atomic_exception(fs, temp_dir):
    """Test atomic file operations with an exception."""
    test_path = os.path.join(temp_dir, "test_exception.txt")

    # Try to write data but raise an exception
    with pytest.raises(RuntimeError):
        with AtomicTextIOWrapper(fs, test_path, "w") as f:
            f.write("This should not be written")
            raise RuntimeError("Test exception")

    # Check the file does not exist
    assert not os.path.exists(test_path)

    # Check that the temporary file was cleaned up
    temp_files = [f for f in os.listdir(temp_dir) if f.startswith(".")]
    assert len(temp_files) == 0
