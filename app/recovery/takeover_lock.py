from __future__ import annotations

import json
import os
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ..config import settings

try:
    import fcntl
except Exception:  # pragma: no cover
    fcntl = None


@dataclass
class LockHandle:
    owner: str
    token: int
    path: str


class FileLockProvider:
    def __init__(self, lock_path: str):
        p = Path(lock_path or (Path(tempfile.gettempdir()) / "archillx_recovery.lock"))
        self.path = p
        self.meta = Path(str(p) + ".json")
        self._fd = None

    def acquire(self, owner: str) -> Optional[LockHandle]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            if fcntl is not None:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            token = int(time.time() * 1000)
            self.meta.write_text(json.dumps({"owner": owner, "token": token, "ts": time.time()}), encoding="utf-8")
            self._fd = fd
            return LockHandle(owner=owner, token=token, path=str(self.path))
        except Exception:
            os.close(fd)
            return None

    def release(self) -> None:
        if self._fd is None:
            return
        try:
            if fcntl is not None:
                fcntl.flock(self._fd, fcntl.LOCK_UN)
        finally:
            os.close(self._fd)
            self._fd = None


class RedisLockProvider:
    def __init__(self, redis_url: str, key: str):
        self._redis = None
        self._key = key
        self._token = None
        if redis_url:
            import redis  # type: ignore
            self._redis = redis.from_url(redis_url)

    def acquire(self, owner: str, ttl_s: int) -> Optional[LockHandle]:
        if self._redis is None:
            return None
        token = int(self._redis.incr(f"{self._key}:fence_seq"))
        payload = json.dumps({"owner": owner, "token": token})
        ok = self._redis.set(self._key, payload, nx=True, ex=max(1, ttl_s))
        if not ok:
            return None
        self._redis.set(f"{self._key}:fence_latest", token)
        self._token = token
        return LockHandle(owner=owner, token=token, path=self._key)

    def renew(self, owner: str, ttl_s: int) -> bool:
        if self._redis is None:
            return False
        val = self._redis.get(self._key)
        if not val:
            return False
        s = val.decode("utf-8") if isinstance(val, bytes) else str(val)
        try:
            parsed = json.loads(s)
        except Exception:
            return False
        if parsed.get("owner") != owner:
            return False
        self._redis.expire(self._key, max(1, ttl_s))
        self._redis.set(f"{self._key}:fence_latest", int(parsed.get("token", 0)))
        return True

    def is_leader(self, token: int) -> bool:
        if self._redis is None:
            return False
        val = self._redis.get(f"{self._key}:fence_latest")
        if not val:
            return False
        latest = int(val.decode("utf-8") if isinstance(val, bytes) else str(val))
        return latest == int(token)

    def release(self, owner: str) -> None:
        if self._redis is None:
            return
        val = self._redis.get(self._key)
        if not val:
            return
        s = val.decode("utf-8") if isinstance(val, bytes) else str(val)
        try:
            parsed = json.loads(s)
        except Exception:
            return
        if parsed.get("owner") == owner:
            self._redis.delete(self._key)


def build_lock_provider():
    backend = (settings.recovery_lock_backend or "file").strip().lower()
    if backend == "redis":
        return RedisLockProvider(settings.redis_url, settings.recovery_lock_key)
    return FileLockProvider(settings.recovery_lock_path)
