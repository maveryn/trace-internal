"""Cross-process locks for review app servers and artifact publishing."""

from __future__ import annotations

from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import socket
from typing import Any, Mapping

_ACTIVE_LOCK_PATHS: set[Path] = set()


class ReviewLockError(RuntimeError):
    """Raised when a review lock is already held by another process."""

    def __init__(self, message: str, *, metadata: Mapping[str, Any] | None = None) -> None:
        super().__init__(message)
        self.metadata = dict(metadata or {})


class ReviewFileLock:
    """Small flock-based lock with JSON metadata for diagnostics."""

    def __init__(self, path: Path | str, *, metadata: Mapping[str, Any] | None = None, blocking: bool = True) -> None:
        self.path = Path(path).resolve()
        self.metadata = dict(metadata or {})
        self.blocking = bool(blocking)
        self._handle: Any | None = None

    def acquire(self) -> "ReviewFileLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle = self.path.open("a+", encoding="utf-8")
        flags = fcntl.LOCK_EX
        if not self.blocking:
            flags |= fcntl.LOCK_NB
        try:
            fcntl.flock(handle.fileno(), flags)
        except BlockingIOError as exc:
            metadata = _read_lock_metadata(handle)
            handle.close()
            raise ReviewLockError(f"review lock is already held: {self.path}", metadata=metadata) from exc

        payload = {
            **self.metadata,
            "pid": int(os.getpid()),
            "host": socket.gethostname(),
            "locked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "lock_path": str(self.path),
        }
        handle.seek(0)
        handle.truncate()
        handle.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
        self._handle = handle
        _ACTIVE_LOCK_PATHS.add(self.path)
        return self

    def release(self) -> None:
        handle = self._handle
        if handle is None:
            return
        self._handle = None
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            _ACTIVE_LOCK_PATHS.discard(self.path)
            handle.close()

    def __enter__(self) -> "ReviewFileLock":
        return self.acquire()

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.release()


def review_file_lock_active(path: Path | str) -> bool:
    """Return whether a review lock appears to be actively held.

    Active locks in this process are tracked explicitly because POSIX locks are
    process-scoped; external holders are detected with a non-blocking flock.
    """

    lock_path = Path(path).resolve()
    if not lock_path.exists():
        return False
    if lock_path in _ACTIVE_LOCK_PATHS:
        return True

    try:
        handle = lock_path.open("a+", encoding="utf-8")
    except OSError:
        return False
    try:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        finally:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
    finally:
        handle.close()
    return False


def review_app_lock_path(*, review_root: Path | str, feedback_db: Path | str) -> Path:
    """Return the single-server lock path for one review root/feedback DB pair."""

    review_root_path = Path(review_root).resolve()
    feedback_db_path = Path(feedback_db).resolve()
    token = _stable_token(str(review_root_path), str(feedback_db_path))
    return review_root_path.parent / ".locks" / f"review_app_{token}.lock"


def scene_publish_lock_path(*, review_root: Path | str, domain: str, scene_id: str) -> Path:
    """Return the publish lock path for one review scene."""

    review_root_path = Path(review_root).resolve()
    token = _stable_token(str(review_root_path), str(domain), str(scene_id))
    safe_domain = _safe_lock_segment(domain)
    safe_scene = _safe_lock_segment(scene_id)
    return review_root_path.parent / ".locks" / f"review_publish_{safe_domain}_{safe_scene}_{token}.lock"


def _read_lock_metadata(handle: Any) -> dict[str, Any]:
    try:
        handle.seek(0)
        payload = json.loads(handle.read() or "{}")
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _stable_token(*parts: str) -> str:
    joined = "\0".join(str(part) for part in parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]


def _safe_lock_segment(value: str) -> str:
    text = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in str(value).strip())
    return text.strip("_") or "unknown"
