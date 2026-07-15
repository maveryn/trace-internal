#!/usr/bin/env python3
"""Safely restart the Trace task-review web app."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import Request, urlopen


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Restart the Trace task-review browser app")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host for the restarted app")
    parser.add_argument("--port", type=int, default=7860, help="Bind port")
    parser.add_argument("--review-root", default="review/task-reviews", help="Review artifact root")
    parser.add_argument("--feedback-db", default="", help="SQLite feedback path")
    parser.add_argument("--token", default="", help="Auth token. Defaults to TRACE_REVIEW_APP_TOKEN.")
    parser.add_argument("--base-url", default=None, help="External URL path prefix passed through to run_review_app.py")
    parser.add_argument("--timeout", type=float, default=20.0, help="Seconds to wait for stop/start health checks")
    parser.add_argument("--log-file", default="logs/review_app/review_app_7860.log", help="Append app logs here")
    return parser.parse_args()


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(int(pid), 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _metadata_pid(payload: dict[str, object]) -> int | None:
    try:
        pid = int(payload.get("pid", 0))
    except (TypeError, ValueError):
        return None
    return pid if pid > 0 else None


def _terminate_existing(pid: int, *, timeout: float) -> None:
    if not _pid_alive(pid):
        return
    os.kill(pid, signal.SIGTERM)
    deadline = time.monotonic() + max(1.0, timeout)
    while time.monotonic() < deadline:
        if not _pid_alive(pid):
            return
        time.sleep(0.1)
    if _pid_alive(pid):
        os.kill(pid, signal.SIGKILL)


def _wait_healthy(*, host: str, port: int, token: str, timeout: float) -> None:
    url = f"http://{host}:{int(port)}/api/reload/status"
    deadline = time.monotonic() + max(1.0, timeout)
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    last_error = ""
    while time.monotonic() < deadline:
        try:
            request = Request(url, headers=headers)
            with urlopen(request, timeout=2.0) as response:
                if 200 <= int(response.status) < 500:
                    return
        except URLError as exc:
            last_error = str(exc)
        except OSError as exc:
            last_error = str(exc)
        time.sleep(0.2)
    raise RuntimeError(f"review app did not become healthy at {url}: {last_error}")


def main() -> int:
    args = _parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from trace.review_app.locks import ReviewFileLock, ReviewLockError, review_app_lock_path

    review_root = Path(args.review_root).resolve()
    feedback_db = (
        Path(args.feedback_db).resolve()
        if str(args.feedback_db).strip()
        else repo_root / "review" / "feedback" / "review_feedback.sqlite"
    )
    lock_path = review_app_lock_path(review_root=review_root, feedback_db=feedback_db)
    pid: int | None = None
    try:
        with ReviewFileLock(lock_path, metadata={"kind": "trace_review_app_restart_probe"}, blocking=False):
            pass
    except ReviewLockError as exc:
        pid = _metadata_pid(exc.metadata)
    if pid is not None:
        _terminate_existing(pid, timeout=float(args.timeout) / 2.0)

    log_path = (repo_root / str(args.log_file)).resolve() if not Path(args.log_file).is_absolute() else Path(args.log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        str(repo_root / "scripts" / "run_review_app.py"),
        "--host",
        str(args.host),
        "--port",
        str(int(args.port)),
        "--review-root",
        str(review_root),
        "--feedback-db",
        str(feedback_db),
    ]
    token = str(args.token or os.environ.get("TRACE_REVIEW_APP_TOKEN", "")).strip()
    if token:
        command.extend(["--token", token])
    if args.base_url is not None:
        command.extend(["--base-url", str(args.base_url)])

    with log_path.open("a", encoding="utf-8") as log_handle:
        process = subprocess.Popen(
            command,
            cwd=str(repo_root),
            stdin=subprocess.DEVNULL,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )

    try:
        _wait_healthy(host=str(args.host), port=int(args.port), token=token, timeout=float(args.timeout))
    except Exception as exc:
        if process.poll() is None:
            print(
                "review app process is still running but did not pass the health check before timeout; "
                f"pid={process.pid}; log={log_path}; error={exc}",
                file=sys.stderr,
            )
            return 4
        raise

    print(f"review app restarted on http://{args.host}:{int(args.port)}; pid={process.pid}; log={log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
