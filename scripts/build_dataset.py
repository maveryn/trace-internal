#!/usr/bin/env python3
"""CLI entrypoint for Trace dataset builds."""

from __future__ import annotations

import argparse
from dataclasses import replace
import sys

from trace.core.builder import BuildError, build_dataset
from trace.core.config import load_build_config


def main() -> int:
    """Parse CLI args and run one dataset build."""
    parser = argparse.ArgumentParser(description="Build Trace dataset from YAML config")
    parser.add_argument("--config", required=True, help="Path to build config YAML")
    parser.add_argument("--code-hash", default="local", help="Code provenance hash")
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Worker processes for generation (0=all visible CPUs, default: config value)",
    )
    parser.add_argument(
        "--max-in-flight",
        type=int,
        default=None,
        help="Max queued generation attempts for multiprocessing (0=2x workers, default: config value)",
    )
    args = parser.parse_args()

    cfg = load_build_config(args.config)
    if args.workers is not None or args.max_in_flight is not None:
        cfg = replace(
            cfg,
            workers=(cfg.workers if args.workers is None else int(args.workers)),
            max_in_flight=(cfg.max_in_flight if args.max_in_flight is None else int(args.max_in_flight)),
        )
    try:
        final_path = build_dataset(cfg, code_hash=args.code_hash)
    except BuildError as exc:
        print(f"build failed: {exc}", file=sys.stderr)
        return 1

    print(str(final_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
