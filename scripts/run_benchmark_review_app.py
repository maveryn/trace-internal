#!/usr/bin/env python3
"""Run the Trace benchmark-review web app."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import socket
import sys


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Trace benchmark-review browser app")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host. Use 0.0.0.0 for remote access.")
    parser.add_argument("--port", type=int, default=7861, help="Preferred bind port")
    parser.add_argument(
        "--port-range",
        default="7861:7899",
        help="Fallback inclusive port range as START:END. Use empty string to disable fallback.",
    )
    parser.add_argument(
        "--run-root",
        default="runs/external_benchmarks/qwen25vl7b/20260522T062435Z",
        help="Benchmark run artifact root",
    )
    parser.add_argument("--token", default="", help="Auth token. Defaults to TRACE_BENCHMARK_REVIEW_APP_TOKEN.")
    parser.add_argument(
        "--base-url",
        default="",
        help="External URL path prefix. Supports {port}; defaults to TRACE_BENCHMARK_REVIEW_APP_BASE_URL.",
    )
    parser.add_argument(
        "--remote-host",
        default=os.environ.get("TRACE_REVIEW_REMOTE_HOST", "95.133.252.216"),
        help="Host used only for printing the remote proxy URL.",
    )
    parser.add_argument("--reload", action="store_true", help="Enable uvicorn development reload")
    return parser.parse_args()


def _requires_token(host: str) -> bool:
    return str(host).strip() not in {"127.0.0.1", "localhost", "::1"}


def _parse_port_range(value: str) -> tuple[int, int] | None:
    text = str(value or "").strip()
    if not text:
        return None
    if ":" not in text:
        port = int(text)
        return port, port
    start, end = text.split(":", 1)
    return int(start), int(end)


def _port_available(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, int(port)))
        except OSError:
            return False
    return True


def _choose_port(host: str, preferred: int, range_text: str) -> int:
    if preferred > 0 and _port_available(host, preferred):
        return preferred
    parsed = _parse_port_range(range_text)
    if parsed is None:
        raise RuntimeError(f"preferred port {preferred} is unavailable and no fallback range was provided")
    start, end = parsed
    for port in range(min(start, end), max(start, end) + 1):
        if preferred > 0 and port == preferred:
            continue
        if _port_available(host, port):
            return port
    raise RuntimeError(f"no free port found in range {start}:{end}")


def main() -> int:
    args = _parse_args()
    token = str(args.token or os.environ.get("TRACE_BENCHMARK_REVIEW_APP_TOKEN", "")).strip()
    if _requires_token(args.host) and not token:
        print(
            "Refusing to bind a remote-access host without auth. "
            "Set TRACE_BENCHMARK_REVIEW_APP_TOKEN or pass --token.",
            file=sys.stderr,
        )
        return 2

    try:
        import uvicorn
    except Exception as exc:
        print(f"uvicorn is not installed: {exc}", file=sys.stderr)
        print("Install requirements.txt before running the benchmark-review app.", file=sys.stderr)
        return 2

    from apps.benchmark_review.server import create_app

    try:
        port = _choose_port(str(args.host), int(args.port), str(args.port_range))
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    repo_root = Path(__file__).resolve().parents[1]
    base_url_template = str(args.base_url or os.environ.get("TRACE_BENCHMARK_REVIEW_APP_BASE_URL", "/proxy/{port}"))
    base_url = base_url_template.format(port=port)
    app = create_app(
        run_root=Path(args.run_root).resolve(),
        repo_root=repo_root,
        token=token,
        base_url=base_url,
    )

    local_url = f"http://{args.host}:{port}/"
    remote_url = f"http://{args.remote_host}:8888{base_url}/" if args.remote_host and base_url else ""
    print(f"Local:  {local_url}", flush=True)
    if remote_url:
        print(f"Remote: {remote_url}", flush=True)
    uvicorn.run(app, host=str(args.host), port=port, reload=bool(args.reload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
