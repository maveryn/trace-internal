#!/usr/bin/env python3
"""Build combined scene-level task-review workbooks."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_task_review import build_scene_review_workbooks  # noqa: E402


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build scene-level TRACE task-review workbooks")
    parser.add_argument(
        "--out-root",
        default="plans/task-reviews",
        help="Task-review root containing <domain>/<scene_id>/<task_id>/ directories",
    )
    parser.add_argument(
        "--scene",
        action="append",
        default=[],
        help="Scene key to rebuild as <domain>/<scene_id>. May be repeated. Defaults to all scenes.",
    )
    return parser.parse_args()


def _parse_scene_keys(raw_scenes: list[str]) -> list[tuple[str, str]] | None:
    if not raw_scenes:
        return None
    scene_keys: list[tuple[str, str]] = []
    for raw in raw_scenes:
        text = str(raw).strip().strip("/")
        parts = [part for part in text.split("/") if part]
        if len(parts) != 2:
            raise ValueError(f"--scene must use <domain>/<scene_id>, got {raw!r}")
        scene_keys.append((str(parts[0]), str(parts[1])))
    return scene_keys


def main() -> int:
    args = _parse_args()
    manifests = build_scene_review_workbooks(
        out_root=Path(str(args.out_root)).resolve(),
        scene_keys=_parse_scene_keys(list(args.scene)),
    )
    print(f"[done] rebuilt {len(manifests)} scene workbooks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
