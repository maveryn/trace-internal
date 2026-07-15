#!/usr/bin/env python3
"""Run the Trace task-review web app."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import sys


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Trace task-review browser app")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host. Use 0.0.0.0 for remote access.")
    parser.add_argument("--port", type=int, default=7860, help="Bind port")
    parser.add_argument("--review-root", default="review/task-reviews", help="Review artifact root")
    parser.add_argument(
        "--feedback-db",
        default="",
        help="SQLite feedback path. Defaults to review/feedback/review_feedback.sqlite.",
    )
    parser.add_argument("--token", default="", help="Auth token. Defaults to TRACE_REVIEW_APP_TOKEN.")
    parser.add_argument(
        "--base-url",
        default=None,
        help=(
            "External URL path prefix, e.g. /proxy/7860 behind Jupyter Server Proxy. "
            "Defaults to TRACE_REVIEW_APP_BASE_URL, then /proxy/{port}. "
            "Pass an empty string or 'none' for root-relative local-only links."
        ),
    )
    parser.add_argument("--reload", action="store_true", help="Enable uvicorn development reload")
    return parser.parse_args()


def _requires_token(host: str) -> bool:
    return str(host).strip() not in {"127.0.0.1", "localhost", "::1"}


def _resolve_base_url(cli_base_url: str | None, *, port: int) -> str:
    """Resolve the browser-facing prefix used for app links and assets."""

    if cli_base_url is not None:
        template = str(cli_base_url)
    elif "TRACE_REVIEW_APP_BASE_URL" in os.environ:
        template = str(os.environ.get("TRACE_REVIEW_APP_BASE_URL", ""))
    else:
        template = "/proxy/{port}"
    text = template.strip()
    if text.lower() in {"", "/", "none", "off", "root"}:
        return ""
    return text.format(port=int(port))


def main() -> int:
    args = _parse_args()
    token = str(args.token or os.environ.get("TRACE_REVIEW_APP_TOKEN", "")).strip()
    if _requires_token(args.host) and not token:
        print(
            "Refusing to bind a remote-access host without auth. "
            "Set TRACE_REVIEW_APP_TOKEN or pass --token.",
            file=sys.stderr,
        )
        return 2

    try:
        import uvicorn
    except Exception as exc:
        print(f"uvicorn is not installed: {exc}", file=sys.stderr)
        print("Install requirements.txt before running the review app.", file=sys.stderr)
        return 2

    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from trace.review_app.server import create_app

    from trace.review_app.locks import ReviewFileLock, ReviewLockError, review_app_lock_path

    review_root = Path(args.review_root).resolve()
    feedback_db = Path(args.feedback_db).resolve() if str(args.feedback_db).strip() else None
    resolved_feedback_db = feedback_db if feedback_db is not None else repo_root / "review" / "feedback" / "review_feedback.sqlite"
    base_url = _resolve_base_url(args.base_url, port=int(args.port))
    lock_path = review_app_lock_path(review_root=review_root, feedback_db=resolved_feedback_db)
    lock_metadata = {
        "kind": "trace_review_app",
        "review_root": str(review_root),
        "feedback_db": str(resolved_feedback_db),
        "host_arg": str(args.host),
        "port": int(args.port),
        "base_url": str(base_url),
        "started_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    try:
        with ReviewFileLock(lock_path, metadata=lock_metadata, blocking=False):
            app = create_app(
                review_root=review_root,
                repo_root=repo_root,
                feedback_db=feedback_db,
                token=token,
                base_url=base_url,
                defer_initial_index=True,
            )
            uvicorn.run(app, host=str(args.host), port=int(args.port), reload=bool(args.reload))
    except ReviewLockError as exc:
        metadata = exc.metadata
        owner = ", ".join(
            f"{key}={metadata[key]}"
            for key in ("pid", "host", "port", "base_url", "review_root")
            if key in metadata
        )
        print(
            "Refusing to start a second Trace review app for the same review root and feedback DB. "
            f"Lock: {lock_path}. Current owner: {owner or 'unknown'}.",
            file=sys.stderr,
        )
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
