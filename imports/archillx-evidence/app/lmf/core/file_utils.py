import os
import sys
import time
import uuid
from contextlib import contextmanager


if sys.platform == 'win32':
    import msvcrt

    @contextmanager
    def file_lock(file_obj, exclusive=True):
        """Windows file locking using msvcrt.locking."""
        fd = file_obj.fileno()
        pos = file_obj.tell()
        file_obj.seek(0)
        try:
            msvcrt.locking(fd, msvcrt.LK_LOCK, 1)
            yield
        finally:
            file_obj.seek(0)
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
            file_obj.seek(pos)

else:
    import fcntl

    @contextmanager
    def file_lock(file_obj, exclusive=True):
        """Unix file locking using fcntl.flock."""
        op = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
        try:
            fcntl.flock(file_obj, op)
            yield
        finally:
            fcntl.flock(file_obj, fcntl.LOCK_UN)


def atomic_write_json(path: str, data: str):
    """Write string data to a file atomically using temp file and rename."""
    dir_name = os.path.dirname(path) or "."
    base_name = os.path.basename(path)

    temp_name = f".{base_name}.{uuid.uuid4()}.tmp"
    temp_path = os.path.join(dir_name, temp_name)

    try:
        with open(temp_path, "w", encoding='utf-8') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())

        max_retries = 10
        if sys.platform == 'win32':
            for i in range(max_retries):
                try:
                    os.replace(temp_path, path)
                    break
                except OSError:
                    if i == max_retries - 1:
                        raise
                    time.sleep(0.05)
        else:
            os.replace(temp_path, path)

    except Exception as e:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
        raise e
