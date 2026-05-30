#!/usr/bin/env python3
"""Run the TRACE task-review web app."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the TRACE task-review browser app")
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
        default="",
        help="External URL path prefix, e.g. /proxy/7860 behind Jupyter Server Proxy. Defaults to TRACE_REVIEW_APP_BASE_URL.",
    )
    parser.add_argument("--reload", action="store_true", help="Enable uvicorn development reload")
    return parser.parse_args()


def _requires_token(host: str) -> bool:
    return str(host).strip() not in {"127.0.0.1", "localhost", "::1"}


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

    from trace.review_app.server import create_app

    repo_root = Path(__file__).resolve().parents[1]
    feedback_db = Path(args.feedback_db).resolve() if str(args.feedback_db).strip() else None
    app = create_app(
        review_root=Path(args.review_root).resolve(),
        repo_root=repo_root,
        feedback_db=feedback_db,
        token=token,
        base_url=str(args.base_url or os.environ.get("TRACE_REVIEW_APP_BASE_URL", "")),
    )
    uvicorn.run(app, host=str(args.host), port=int(args.port), reload=bool(args.reload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
