"""
Pytest fixtures for fsbridge tests.
"""

import os
import shutil
import tempfile
import pytest

from fsbridge.mapping import create_fs_mapping
from fsbridge.utils import create_fsspec_fs


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def temp_dir2():
    """Create a second temporary directory for tests."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def fs():
    """Create a filesystem for tests."""
    return create_fsspec_fs("file")


@pytest.fixture
def path_mapper(temp_dir):
    """Create a path mapper function for tests."""

    def mapper(path, operation):
        if path and path.startswith("/test/"):
            mapped_path = os.path.join(temp_dir, path[6:])
            return True, mapped_path
        return False, path

    return mapper


@pytest.fixture
def fs_mapping(fs, path_mapper):
    """Create a mapping for tests."""
    return create_fs_mapping(fs=fs, path_mapping=path_mapper)


@pytest.fixture
def dict_mapping(temp_dir):
    """Create a mapping with dictionary path mapping."""
    return create_fs_mapping(path_mapping={"/test/": temp_dir})
