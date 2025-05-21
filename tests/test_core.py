"""
Tests for the FSBridgeContext class.
"""

import os
from pathlib import Path
import pytest

from fsbridge.core import FSBridgeContext


def test_context_open(fs_mapping, temp_dir):
    """Test the context manager with open."""
    test_file = "/test/test.txt"
    test_content = "Hello, world!"

    with FSBridgeContext(fs_mapping):
        # Write to the file
        with open(test_file, "w") as f:
            f.write(test_content)

        # Read from the file
        with open(test_file, "r") as f:
            content = f.read()

        assert content == test_content

    # Verify the file was created in the right place
    real_path = os.path.join(temp_dir, "test.txt")
    assert os.path.exists(real_path)

    with open(real_path, "r") as f:
        content = f.read()

    assert content == test_content


def test_context_pathlib(fs_mapping, temp_dir):
    """Test the context manager with pathlib."""
    test_dir = Path("/test/subdir")
    test_file = test_dir / "test.txt"
    test_content = "Hello, pathlib!"

    with FSBridgeContext(fs_mapping):
        # Create directory
        test_dir.mkdir(exist_ok=True)

        # Write to the file
        test_file.write_text(test_content)

        # Read from the file
        content = test_file.read_text()

        assert content == test_content

    # Verify the file was created in the right place
    real_path = os.path.join(temp_dir, "subdir", "test.txt")
    assert os.path.exists(real_path)

    with open(real_path, "r") as f:
        content = f.read()

    assert content == test_content


def test_context_os(fs_mapping, temp_dir):
    """Test the context manager with os."""
    test_dir = "/test/osdir"
    test_file = os.path.join(test_dir, "test.txt")
    test_content = "Hello, os!"

    with FSBridgeContext(fs_mapping):
        # Create directory
        os.makedirs(test_dir, exist_ok=True)

        # Write to the file
        with open(test_file, "w") as f:
            f.write(test_content)

        # List directory
        files = os.listdir(test_dir)
        assert "test.txt" in files

        # Check file exists
        assert os.path.exists(test_file)
        assert os.path.isfile(test_file)

        # Get file size
        size = os.path.getsize(test_file)
        assert size == len(test_content)

    # Verify the file was created in the right place
    real_path = os.path.join(temp_dir, "osdir", "test.txt")
    assert os.path.exists(real_path)


def test_context_shutil(fs_mapping, temp_dir):
    """Test the context manager with shutil."""
    import shutil

    test_dir = "/test/shutil"
    test_file = os.path.join(test_dir, "test.txt")
    test_file2 = os.path.join(test_dir, "test2.txt")
    test_content = "Hello, shutil!"

    with FSBridgeContext(fs_mapping):
        # Create directory
        os.makedirs(test_dir, exist_ok=True)

        # Write to the file
        with open(test_file, "w") as f:
            f.write(test_content)

        # Copy file
        shutil.copy(test_file, test_file2)

        # Check file exists
        assert os.path.exists(test_file2)

        # Read the copied file
        with open(test_file2, "r") as f:
            content = f.read()

        assert content == test_content

    # Verify the files were created in the right place
    real_path = os.path.join(temp_dir, "shutil", "test.txt")
    real_path2 = os.path.join(temp_dir, "shutil", "test2.txt")
    assert os.path.exists(real_path)
    assert os.path.exists(real_path2)


def test_selective_patching(fs_mapping, temp_dir):
    """Test selective patching of functions."""
    test_file = "/test/selective.txt"
    test_content = "Hello, selective!"

    # Test with only open patched
    with FSBridgeContext(
        fs_mapping,
        patch_open=True,
        patch_os=False,
        patch_pathlib=False,
        patch_shutil=False,
    ):
        # Write to the file (should be redirected)
        with open(test_file, "w") as f:
            f.write(test_content)

        # os.path.exists should not be redirected
        # This will return False because we're checking the local filesystem
        assert not os.path.exists(test_file)

    # Verify the file was created in the right place
    real_path = os.path.join(temp_dir, "selective.txt")
    assert os.path.exists(real_path)
