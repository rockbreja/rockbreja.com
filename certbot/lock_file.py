"""Implements simple UNIX file locking."""
import errno
import fcntl
import os

from certbot import errors


class LockFile(object):
    """A UNIX file lock.

    This class implements a simple UNIX lock file to provide
    synchronization between processes. This lock file cannot be used to
    provide synchronization between threads. This class works best as a
    context manager to help ensure the lock is properly cleaned up and
    released.

    This lock file is based on the lock_file package by Martin Horcicka.

    """
    def __init__(self, path):
        self._fd = None
        self._path = path

    def __enter__(self):
        self.acquire()

    def __exit__(self, exc_type, exc_value, traceback):
        self.release()

    def __repr__(self):
        return "{0}({1})".format(self.__class__.__name__, self._path)

    def acquire(self):
        """Acquire the lock on the lockfile.

        :raises .LockError: If the lock file is held by another process.

        """
        # Acquire the lock file
        while self._fd is None:
            # Open the file
            fd = os.open(self._path, os.O_CREAT | os.O_WRONLY, 0666)
            try:
                # Acquire an exclusive lock
                try:
                    fcntl.lockf(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except IOError, e:
                    if e.errno in (errno.EACCES, errno.EAGAIN):
                        raise errors.LockError(
                            "Another instance of Certbot is already running.")
                    else:
                        raise
                # Check if the locked file is the required one (it could
                # have been removed and possibly recreated between the
                # opening and the lock acquisition)
                try:
                    stat1 = os.stat(self._path)
                except OSError, e:
                    if e.errno != errno.ENOENT:
                        raise
                else:
                    stat2 = os.fstat(fd)
                    if _is_same_file(stat1, stat2):
                        self._fd = fd
            finally:
                # Close the file if it is not the required one
                if self._fd is None:
                    os.close(fd)

    def release(self):
        """Release the lock file."""
        # Remove and close the file
        try:
            os.remove(self._path)
        finally:
            try:
                os.close(self._fd)
            finally:
                self._fd = None


def _is_same_file(stat1, stat2):
    """Do stat1 and stat2 refer to the same file?"""
    return stat1.st_dev == stat2.st_dev and stat1.st_ino == stat2.st_ino
