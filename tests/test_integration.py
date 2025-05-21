"""
Integration tests for fsbridge.
"""

import os
from pathlib import Path
import pytest

from fsbridge import fsbridge_context


def test_basic_usage(temp_dir):
    """Test basic usage with dictionary path mapping."""
    test_file = "/outputs/results.csv"
    test_content = "data,value\n1,2\n"

    with fsbridge_context(path_mapping={"/outputs/": temp_dir}):
        # Write to the file
        with open(test_file, "w") as f:
            f.write(test_content)

        # Create a directory
        Path("/outputs/subdir").mkdir(exist_ok=True)

        # Copy a file
        with open("/outputs/source.txt", "w") as f:
            f.write("Source content")

        import shutil

        shutil.copy("/outputs/source.txt", "/outputs/destination.txt")

    # Verify the files were created in the right place
    csv_path = os.path.join(temp_dir, "results.csv")
    subdir_path = os.path.join(temp_dir, "subdir")
    dest_path = os.path.join(temp_dir, "destination.txt")

    assert os.path.exists(csv_path)
    assert os.path.isdir(subdir_path)
    assert os.path.exists(dest_path)

    with open(csv_path, "r") as f:
        content = f.read()

    assert content == test_content


def test_custom_mapper(temp_dir):
    """Test using a custom path mapper function."""

    # Custom path mapper that redirects only CSV files
    def csv_mapper(path, operation):
        if isinstance(path, str) and path.endswith(".csv"):
            return True, os.path.join(temp_dir, os.path.basename(path))
        return False, path

    with fsbridge_context(path_mapping=csv_mapper):
        # This will be redirected
        with open("data.csv", "w") as f:
            f.write("data,value\n1,2\n")

        # This will not be redirected
        local_txt = os.path.join(temp_dir, "local.txt")
        with open(local_txt, "w") as f:
            f.write("Hello, world!\n")

    # Verify the CSV file was created in the tempdir
    csv_path = os.path.join(temp_dir, "data.csv")
    assert os.path.exists(csv_path)

    # Verify the text file was written directly
    with open(local_txt, "r") as f:
        content = f.read()

    assert content == "Hello, world!\n"


def test_multiple_filesystems(temp_dir, temp_dir2):
    """Test using multiple target paths."""
    # Map multiple paths to different targets
    path_mapping = {
        "/data/": temp_dir,
        "/logs/": temp_dir2,
    }

    with fsbridge_context(path_mapping=path_mapping):
        # Each path will be redirected to its corresponding target
        with open("/data/file.csv", "w") as f:
            f.write("data\n")

        with open("/logs/app.log", "w") as f:
            f.write("log entry\n")

    # Verify the files were created in the right places
    data_path = os.path.join(temp_dir, "file.csv")
    log_path = os.path.join(temp_dir2, "app.log")

    assert os.path.exists(data_path)
    assert os.path.exists(log_path)

    with open(data_path, "r") as f:
        content = f.read()

    assert content == "data\n"

    with open(log_path, "r") as f:
        content = f.read()

    assert content == "log entry\n"
