"""
Atomic file operations support.

This module provides classes to perform atomic write operations
with fsspec filesystems.
"""

import os
import io


class AtomicFileWrapper:
    """
    Wrapper for binary files that provides atomic write operations.

    This class buffers writes to a temporary file and only replaces the
    target file when the operation is complete.
    """

    def __init__(self, fs, path, mode, suffix=".tmp", prefix=".", **kwargs):
        self.fs = fs
        self.path = path
        self.mode = mode
        self.suffix = suffix
        self.prefix = prefix
        self.kwargs = kwargs

        # Create temporary file path
        dirname = os.path.dirname(self.path)
        basename = os.path.basename(self.path)
        self.temp_path = f"{dirname}/{self.prefix}{basename}{self.suffix}"

        # Open temporary file
        self.file = fs.open(self.temp_path, mode, **kwargs)
        self.closed = False

    def write(self, data):
        """Write data to the temporary file."""
        return self.file.write(data)

    def read(self, size=-1):
        """Read from the file."""
        return self.file.read(size)

    def close(self):
        """Close the file and move it to the final destination."""
        if self.closed:
            return

        self.file.close()

        # Only move the file if we were writing
        if "w" in self.mode or "a" in self.mode or "+" in self.mode:
            try:
                # Remove destination if it exists
                if self.fs.exists(self.path):
                    self.fs.rm(self.path)
                # Move temp file to destination
                self.fs.mv(self.temp_path, self.path)
            except Exception as e:
                # If moving fails, try to clean up the temp file
                try:
                    self.fs.rm(self.temp_path)
                except:
                    pass
                raise e

        self.closed = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # An exception occurred, discard the temp file
            self.file.close()
            try:
                self.fs.rm(self.temp_path)
            except:
                pass
            self.closed = True
        else:
            # No exception, close normally (which moves the file)
            self.close()

    def __getattr__(self, name):
        """Delegate all other attributes to the underlying file object."""
        return getattr(self.file, name)


class AtomicTextIOWrapper:
    """
    Wrapper for text files that provides atomic write operations.

    This is a text-mode version of AtomicFileWrapper that properly
    handles encoding and newlines.
    """

    def __init__(
        self,
        fs,
        path,
        mode,
        suffix=".tmp",
        prefix=".",
        encoding=None,
        errors=None,
        newline=None,
        **kwargs,
    ):
        # Create binary wrapper
        self.binary_wrapper = AtomicFileWrapper(
            fs, path, mode.replace("t", "") + "b", suffix, prefix, **kwargs
        )

        # Wrap with TextIOWrapper
        self.wrapper = io.TextIOWrapper(
            self.binary_wrapper, encoding=encoding, errors=errors, newline=newline
        )

    def write(self, data):
        """Write data to the wrapped text file."""
        return self.wrapper.write(data)

    def read(self, size=-1):
        """Read from the wrapped text file."""
        return self.wrapper.read(size)

    def close(self):
        """Close the wrapped text file."""
        self.wrapper.close()

    def __enter__(self):
        return self.wrapper

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self.wrapper.__exit__(exc_type, exc_val, exc_tb)

    def __getattr__(self, name):
        """Delegate all other attributes to the underlying text file object."""
        return getattr(self.wrapper, name)
