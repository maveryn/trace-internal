#!/usr/bin/env python3
"""Audit physics task-review freshness against generation inputs.

This audit is intentionally scoped to files that can change generated physics
review samples: physics task source, shared task helpers used by physics,
prompt assets, task docs, and domain/scene configs. Domain migration reports
are excluded so editing this report does not make task-review artifacts stale.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Iterable, Sequence


DOMAIN = "physics"
DEFAULT_REVIEW_ROOT = Path("review/task-reviews")
DEFAULT_OUT_DIR = Path("docs/domain-migration-report/physics")
DEFAULT_JSON_REPORT = DEFAULT_OUT_DIR / "review_freshness_audit.json"
DEFAULT_MD_REPORT = DEFAULT_OUT_DIR / "review_freshness_audit.md"
SCHEMA_ID = "trace_physics_review_freshness_audit_v1"

SKIP_DIR_NAMES = frozenset({"__pycache__", ".ipynb_checkpoints", ".pytest_cache", ".mypy_cache"})
SKIP_SUFFIXES = frozenset({".pyc", ".pyo", ".swp", ".tmp"})


@dataclass(frozen=True)
class FileStamp:
    path: str
    mtime: float
    iso_mtime: str


def collect_report(
    *,
    review_root: Path,
    out_dir: Path,
) -> dict[str, Any]:
    root = Path(".")
    scene_ids = _scene_ids(root / "docs/tasks" / DOMAIN)
    records: list[dict[str, Any]] = []

    for scene_id in scene_ids:
        marker = review_root / DOMAIN / scene_id / "scene_review_manifest.json"
        inputs = list(_scene_input_files(root=root, scene_id=scene_id, out_dir=out_dir))
        newest_input = _newest_file(inputs)
        missing_marker = not marker.exists()
        marker_mtime = marker.stat().st_mtime if marker.exists() else None
        stale = bool(missing_marker or (newest_input is not None and marker_mtime is not None and newest_input.mtime > marker_mtime))
        records.append(
            {
                "scene_id": scene_id,
                "status": "missing_manifest" if missing_marker else ("stale" if stale else "fresh"),
                "stale": stale,
                "manifest_path": str(marker),
                "manifest_mtime": marker_mtime,
                "manifest_iso_mtime": _iso(marker_mtime) if marker_mtime is not None else None,
                "input_count": len(inputs),
                "newest_input": newest_input.__dict__ if newest_input is not None else None,
            }
        )

    scene_review_workbooks = sorted((review_root / DOMAIN).glob("*/scene_review.xlsx"))
    task_workbooks = sorted((review_root / DOMAIN).glob("*/*/task_physics__*.xlsx"))
    stale_records = [record for record in records if record["status"] == "stale"]
    missing_records = [record for record in records if record["status"] == "missing_manifest"]
    totals = {
        "scene_count": len(scene_ids),
        "fresh_scene_count": sum(1 for record in records if record["status"] == "fresh"),
        "stale_scene_count": len(stale_records),
        "missing_manifest_count": len(missing_records),
        "scene_review_workbook_count": len(scene_review_workbooks),
        "task_review_workbook_count": len(task_workbooks),
        "pass": not stale_records and not missing_records,
    }
    return {
        "schema": SCHEMA_ID,
        "checked_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "domain": DOMAIN,
        "review_root": str(review_root),
        "freshness_marker": "scene_review_manifest.json",
        "excluded_report_root": str(out_dir),
        "input_policy": [
            "trace/tasks/physics/<scene_id>/",
            "trace/tasks/physics/shared/",
            "trace/tasks/shared/",
            "prompts/physics/<scene_id>/",
            "docs/tasks/physics/<scene_id>/",
            "configs/domains/physics/base.yaml",
            "configs/domains/physics/<scene_id>.yaml",
            "docs/SCENE_PACKAGE_MIGRATION/PHYSICS_SHARED_BOUNDARY.md",
        ],
        "totals": totals,
        "records": records,
    }


def render_markdown(report: dict[str, Any]) -> str:
    totals = report["totals"]
    lines = [
        "# Physics Review Freshness Audit",
        "",
        f"- Checked at: `{report['checked_at']}`",
        f"- Review root: `{report['review_root']}`",
        f"- Freshness marker: `{report['freshness_marker']}`",
        f"- Excluded report root: `{report['excluded_report_root']}`",
        f"- Scenes checked: `{totals['scene_count']}`",
        f"- Fresh scenes: `{totals['fresh_scene_count']}`",
        f"- Stale scenes: `{totals['stale_scene_count']}`",
        f"- Missing scene manifests: `{totals['missing_manifest_count']}`",
        f"- Scene workbooks present: `{totals['scene_review_workbook_count']}`",
        f"- Task workbooks present: `{totals['task_review_workbook_count']}`",
        f"- Pass: `{totals['pass']}`",
        "",
        "## Input Policy",
        "",
    ]
    for item in report["input_policy"]:
        lines.append(f"- `{item}`")

    attention = [record for record in report["records"] if record["status"] != "fresh"]
    if attention:
        lines.extend(["", "## Attention Needed", "", "| Scene | Status | Newest input | Manifest |", "| --- | --- | --- | --- |"])
        for record in attention:
            newest = record.get("newest_input") or {}
            newest_text = newest.get("path", "")
            if newest.get("iso_mtime"):
                newest_text += f" ({newest['iso_mtime']})"
            manifest_text = record["manifest_path"]
            if record.get("manifest_iso_mtime"):
                manifest_text += f" ({record['manifest_iso_mtime']})"
            lines.append(f"| `{record['scene_id']}` | `{record['status']}` | `{newest_text}` | `{manifest_text}` |")
    else:
        lines.extend(["", "## Attention Needed", "", "None."])

    return "\n".join(lines).rstrip() + "\n"


def write_report(report: dict[str, Any], *, json_path: Path, md_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")


def _scene_ids(docs_root: Path) -> list[str]:
    scene_ids = {
        path.parent.name
        for path in docs_root.glob("*/task_physics__*.md")
        if path.is_file()
    }
    return sorted(scene_ids)


def _scene_input_files(*, root: Path, scene_id: str, out_dir: Path) -> Iterable[Path]:
    candidates: Sequence[Path] = (
        root / "trace/tasks" / DOMAIN / scene_id,
        root / "trace/tasks" / DOMAIN / "shared",
        root / "trace/tasks/shared",
        root / "prompts" / DOMAIN / scene_id,
        root / "docs/tasks" / DOMAIN / scene_id,
        root / "configs/domains" / DOMAIN / "base.yaml",
        root / "configs/domains" / DOMAIN / f"{scene_id}.yaml",
        root / "docs/SCENE_PACKAGE_MIGRATION/PHYSICS_SHARED_BOUNDARY.md",
    )
    excluded_root = out_dir.resolve()
    seen: set[Path] = set()
    for candidate in candidates:
        for path in _iter_files(candidate):
            resolved = path.resolve()
            if resolved in seen or _is_relative_to(resolved, excluded_root):
                continue
            seen.add(resolved)
            yield path


def _iter_files(path: Path) -> Iterable[Path]:
    if path.is_file():
        if _include_file(path):
            yield path
        return
    if not path.is_dir():
        return
    for item in path.rglob("*"):
        if not item.is_file() or not _include_file(item):
            continue
        if any(part in SKIP_DIR_NAMES for part in item.parts):
            continue
        yield item


def _include_file(path: Path) -> bool:
    if path.name.startswith("."):
        return False
    if path.suffix in SKIP_SUFFIXES:
        return False
    return True


def _newest_file(paths: Sequence[Path]) -> FileStamp | None:
    newest: FileStamp | None = None
    for path in paths:
        mtime = path.stat().st_mtime
        stamp = FileStamp(path=str(path), mtime=mtime, iso_mtime=_iso(mtime))
        if newest is None or stamp.mtime > newest.mtime:
            newest = stamp
    return newest


def _iso(mtime: float) -> str:
    return datetime.fromtimestamp(mtime, timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-root", type=Path, default=DEFAULT_REVIEW_ROOT)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--json-report", type=Path, default=DEFAULT_JSON_REPORT)
    parser.add_argument("--md-report", type=Path, default=DEFAULT_MD_REPORT)
    args = parser.parse_args()

    report = collect_report(review_root=args.review_root, out_dir=args.out_dir)
    write_report(report, json_path=args.json_report, md_path=args.md_report)
    totals = report["totals"]
    print(f"physics scenes checked: {totals['scene_count']}")
    print(f"stale scenes: {totals['stale_scene_count']}")
    print(f"missing scene manifests: {totals['missing_manifest_count']}")
    print(f"scene workbooks present: {totals['scene_review_workbook_count']}")
    print(f"task workbooks present: {totals['task_review_workbook_count']}")
    return 0 if totals["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
