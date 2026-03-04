#!/usr/bin/env python3
"""Cleanup helper for failed TRACE builds (dry-run by default)."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path
from typing import List


def _collect_targets(output_root: Path) -> List[Path]:
    targets: List[Path] = []
    tmp_root = output_root / "tmp"
    failed_root = output_root / "failed_builds"
    if tmp_root.exists():
        targets.extend(sorted([path for path in tmp_root.iterdir() if path.is_dir()]))
    if failed_root.exists():
        targets.extend(sorted([path for path in failed_root.iterdir() if path.is_dir()]))
    return targets


def main() -> int:
    parser = argparse.ArgumentParser(description="Cleanup failed TRACE build artifacts")
    parser.add_argument("--output-root", default="./out", help="Build output root")
    parser.add_argument("--apply", action="store_true", help="Actually delete targets")
    args = parser.parse_args()

    output_root = Path(args.output_root)
    targets = _collect_targets(output_root)

    if not targets:
        print("no cleanup targets found")
        return 0

    print("cleanup targets:")
    for target in targets:
        print(str(target))

    if not args.apply:
        print("dry-run only; re-run with --apply to delete")
        return 0

    for target in targets:
        shutil.rmtree(target)
    print(f"deleted {len(targets)} targets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
