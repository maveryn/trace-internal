#!/usr/bin/env python3
"""CLI entrypoint for TRACE dataset builds."""

from __future__ import annotations

import argparse
import sys

from trace.core.builder import BuildError, build_dataset
from trace.core.config import load_build_config


def main() -> int:
    parser = argparse.ArgumentParser(description="Build TRACE dataset from YAML config")
    parser.add_argument("--config", required=True, help="Path to build config YAML")
    parser.add_argument("--code-hash", default="local", help="Code provenance hash")
    args = parser.parse_args()

    cfg = load_build_config(args.config)
    try:
        final_path = build_dataset(cfg, code_hash=args.code_hash)
    except BuildError as exc:
        print(f"build failed: {exc}", file=sys.stderr)
        return 1

    print(str(final_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
