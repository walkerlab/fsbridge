# fsbridge

A pragmatic monkey-patching library that transparently redirects Python's standard file operations to FSSpec backends, allowing existing code to work with any filesystem without modification.

[![PyPI version](https://badge.fury.io/py/fsbridge.svg)](https://badge.fury.io/py/fsbridge)
[![Python Versions](https://img.shields.io/pypi/pyversions/fsbridge.svg)](https://pypi.org/project/fsbridge/)
[![License](https://img.shields.io/github/license/yourusername/fsbridge.svg)](https://github.com/yourusername/fsbridge/blob/main/LICENSE)

## Why fsbridge?

When working with libraries that use Python's standard file operations (`open()`, `os.path`, `pathlib.Path`, etc.), you often need to:

- Redirect file outputs to a different location
- Support cloud storage or other non-local filesystems
- Guarantee atomic file operations
- Handle virtual file paths

Normally, this would require rewriting code to use [FSSpec](https://filesystem-spec.readthedocs.io/) directly. **fsbridge** eliminates this need by transparently redirecting standard Python file operations to FSSpec backends through monkey-patching.

## Installation

```bash
pip install fsbridge
```

## Quick Start

```python
from fsbridge import fsbridge_context

# Redirect all operations on paths beginning with '/outputs/' to '/tmp/actual_outputs/'
with fsbridge_context('/tmp/actual_outputs', path_prefix='/outputs/'):
    # Standard file operations work as expected, but are redirected
    with open('/outputs/results.csv', 'w') as f:
        f.write('data,value\n1,2\n')
    
    # Works with pathlib too
    from pathlib import Path
    output_dir = Path('/outputs/subdir')
    output_dir.mkdir(exist_ok=True)
    
    # Even works with os and shutil operations
    import os
    import shutil
    os.makedirs('/outputs/another/nested/dir', exist_ok=True)
    shutil.copy('source.txt', '/outputs/destination.txt')
```

## Features

- **Transparent redirection**: No changes needed to existing code
- **Atomic file operations**: All write operations are atomic by default
- **Comprehensive coverage**: Supports `open()`, `pathlib.Path`, `os.*`, `shutil.*`, and more
- **FSSpec compatibility**: Works with any FSSpec backend (local, S3, GCS, HTTP, etc.)
- **Context-based**: Changes are only applied within the context manager
- **Customizable**: Configure path prefixes, atomic behavior, and more

## How It Works

fsbridge uses monkey-patching to intercept standard Python file operations and redirect them to FSSpec. While monkey-patching is generally considered a "dirty" approach, it's used here pragmatically to solve a real problem: allowing existing code to work with any filesystem without modification.

Inside the `fsbridge_context`:

1. Standard Python file operations are monkey-patched
2. Operations matching the path prefix are redirected to the specified filesystem
3. Write operations are performed atomically through temporary files
4. When the context exits, original functions are restored

## Advanced Usage

### Using with S3 Storage

```python
import s3fs
from fsbridge import fsbridge_context, create_fsspec_fs

# Create an S3 filesystem
s3 = s3fs.S3FileSystem(anon=False)

# Redirect '/outputs/' paths to an S3 bucket
with fsbridge_context('my-bucket/outputs', fs=s3, path_prefix='/outputs/'):
    # This will write to S3 atomically
    with open('/outputs/results.csv', 'w') as f:
        f.write('data,value\n1,2\n')
```

### Customizing Atomic Behavior

```python
from fsbridge import fsbridge_context

with fsbridge_context('/tmp/outputs', path_prefix='/outputs/', 
                      atomic_writes=True, atomic_suffix='.temp',
                      atomic_prefix='.tmp.'):
    # Customize how atomic operations work
    with open('/outputs/file.txt', 'w') as f:
        f.write('data')
```

### Selective Patching

```python
from fsbridge import fsbridge_context

with fsbridge_context('/tmp/outputs', path_prefix='/outputs/',
                      patch_open=True, patch_os=True, 
                      patch_pathlib=True, patch_shutil=False):
    # Only selected modules will be patched
    pass
```

### Explicit Usage (No Monkey-Patching)

```python
from fsbridge import create_fsspec_mapping

# Get a mapped filesystem without monkey-patching
fs = create_fsspec_mapping('/tmp/outputs', path_prefix='/outputs/')

# Use the filesystem explicitly
with fs.open('/outputs/file.txt', 'w') as f:
    f.write('data')
```

## Supported Operations

fsbridge redirects the following operations:

- **builtins**: `open()`
- **pathlib**: `Path()`, `Path.open()`, `Path.mkdir()`, etc.
- **os**: `os.path.exists()`, `os.makedirs()`, `os.mkdir()`, `os.rename()`, etc.
- **os.path**: `exists()`, `isdir()`, `isfile()`, etc.
- **shutil**: `copyfile()`, `copy()`, `copy2()`, `move()`, etc.

## Limitations

fsbridge has some limitations you should be aware of:

1. **Performance overhead**: The monkey-patching and redirection add some overhead
2. **Not all operations supported**: Some specialized file operations might not work as expected
3. **Thread safety**: Be cautious when using in multi-threaded environments
4. **C extensions**: Python modules implemented in C might bypass the Python-level monkey patching

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [FSSpec](https://filesystem-spec.readthedocs.io/) for providing the filesystem abstraction
- [PyFilesystem2](https://docs.pyfilesystem.org/) for inspiration
- [pyfakefs](https://github.com/jmcgeheeiv/pyfakefs) for demonstrating effective file operation monkey-patching
