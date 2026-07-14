#!/usr/bin/env python3
"""Remove task-audit rows for retired task ids from the review feedback DB."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any, Iterable


DEFAULT_FEEDBACK_DB = Path("review/feedback/review_feedback.sqlite")
DEFAULT_REVIEW_ROOT = Path("review/task-reviews")
DEFAULT_OUTPUT_ROOT = Path("review/feedback-cleanup")
DEFAULT_UPDATED_BY = "retired_task_audit_cleanup"
SCHEMA_ID = "trace_retired_task_audit_cleanup_v0"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _timestamp_slug(timestamp: str) -> str:
    return (
        str(timestamp)
        .replace(":", "")
        .replace("+", "Z")
        .replace("-", "")
        .replace(".", "")
    )


def _connect_existing_feedback_db(feedback_db: Path) -> sqlite3.Connection:
    if not feedback_db.exists():
        raise FileNotFoundError(f"feedback DB does not exist: {feedback_db}")
    conn = sqlite3.connect(feedback_db, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def _row_payload(row: sqlite3.Row) -> dict[str, Any]:
    return {str(key): row[key] for key in row.keys()}


def _active_review_task_keys(*, review_root: Path, domain: str) -> set[tuple[str, str, str]]:
    """Return active task keys from current task-review manifests for one domain."""

    domain_root = Path(review_root) / str(domain)
    if not domain_root.exists():
        raise FileNotFoundError(f"review domain root does not exist: {domain_root}")
    keys: set[tuple[str, str, str]] = set()
    for manifest_path in sorted(domain_root.glob("*/*/manifest.json")):
        scene_id = str(manifest_path.parent.parent.name)
        task_id = str(manifest_path.parent.name)
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid task review manifest JSON: {manifest_path}") from exc
        manifest_task_id = str(manifest.get("task_id") or task_id)
        if manifest_task_id != task_id:
            raise ValueError(
                f"task review manifest path/task mismatch: {manifest_path} has {manifest_task_id!r}"
            )
        keys.add((str(domain), scene_id, task_id))
    if not keys:
        raise ValueError(f"no active task-review manifests found under {domain_root}")
    return keys


def _backup_database(feedback_db: Path, *, output_root: Path, timestamp_slug: str) -> Path:
    output_root.mkdir(parents=True, exist_ok=True)
    backup_path = output_root / f"{feedback_db.name}.retired_task_audit_cleanup_{timestamp_slug}.bak"
    with sqlite3.connect(feedback_db, timeout=30.0) as source, sqlite3.connect(backup_path) as backup:
        source.execute("PRAGMA busy_timeout=30000")
        source.execute("PRAGMA wal_checkpoint(FULL)")
        source.backup(backup)
    return backup_path


def _write_report_files(report: dict[str, Any], *, output_root: Path, timestamp_slug: str) -> tuple[Path, Path]:
    output_root.mkdir(parents=True, exist_ok=True)
    json_path = output_root / f"retired_task_audit_cleanup_{timestamp_slug}.json"
    md_path = output_root / f"retired_task_audit_cleanup_{timestamp_slug}.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(_render_markdown_report(report), encoding="utf-8")
    return json_path, md_path


def _render_markdown_report(report: dict[str, Any]) -> str:
    mode = "applied" if report.get("applied") else "dry run"
    lines = [
        "# Retired Task Audit Cleanup",
        "",
        f"- schema: `{report['schema']}`",
        f"- generated_at: `{report['generated_at']}`",
        f"- mode: `{mode}`",
        f"- domain: `{report['domain']}`",
        f"- feedback_db: `{report['feedback_db']}`",
        f"- review_root: `{report['review_root']}`",
        f"- active_review_task_count: `{report['active_review_task_count']}`",
        f"- db_task_audit_rows_before: `{report['db_task_audit_rows_before']}`",
        f"- stale_row_count_before: `{report['stale_row_count_before']}`",
        f"- deleted_row_count: `{report['deleted_row_count']}`",
        f"- db_task_audit_rows_after: `{report['db_task_audit_rows_after']}`",
        f"- stale_row_count_after: `{report['stale_row_count_after']}`",
        f"- backup_path: `{report.get('backup_path', '')}`",
        "",
        "## Deleted Rows" if report.get("applied") else "## Rows That Would Be Deleted",
        "",
    ]
    stale_rows = list(report.get("stale_rows_before", []))
    if not stale_rows:
        lines.append("None.")
    else:
        lines.extend(
            [
                "| scene_id | task_id | prompt | image | annotation | distribution | code | taxonomy | supervision | solve_rate | updated_at | updated_by |",
                "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |",
            ]
        )
        for row in stale_rows:
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(row.get("scene_id", "")),
                        str(row.get("task_id", "")),
                        str(int(row.get("prompt_pass") or 0)),
                        str(int(row.get("image_pass") or 0)),
                        str(int(row.get("annotation_pass") or 0)),
                        str(int(row.get("distribution_pass") or 0)),
                        str(int(row.get("code_review_pass") or 0)),
                        str(int(row.get("taxonomy_review_pass") or 0)),
                        str(int(row.get("supervision_review_pass") or 0)),
                        str(int(row.get("solve_rate_pass") or 0)),
                        str(row.get("updated_at", "")),
                        str(row.get("updated_by", "")),
                    ]
                )
                + " |"
            )
    lines.append("")
    return "\n".join(lines)


def _summarize_rows(rows: Iterable[sqlite3.Row]) -> dict[str, int]:
    counts = Counter(str(row["scene_id"]) for row in rows)
    return {str(scene_id): int(count) for scene_id, count in sorted(counts.items())}


def cleanup_retired_task_audit_rows(
    *,
    domain: str,
    feedback_db: Path = DEFAULT_FEEDBACK_DB,
    review_root: Path = DEFAULT_REVIEW_ROOT,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    apply: bool = False,
    backup: bool = True,
) -> dict[str, Any]:
    """Delete task-audit rows whose task id no longer has review artifacts."""

    domain = str(domain)
    feedback_db = Path(feedback_db)
    review_root = Path(review_root)
    output_root = Path(output_root)
    generated_at = _now()
    timestamp_slug = _timestamp_slug(generated_at)
    active_keys = _active_review_task_keys(review_root=review_root, domain=domain)
    backup_path = ""

    with _connect_existing_feedback_db(feedback_db) as conn:
        rows_before = conn.execute(
            "SELECT * FROM task_audit WHERE domain = ? ORDER BY scene_id, task_id",
            (domain,),
        ).fetchall()
        stale_rows = [
            row
            for row in rows_before
            if (str(row["domain"]), str(row["scene_id"]), str(row["task_id"])) not in active_keys
        ]

        if apply and stale_rows:
            if backup:
                backup_path = str(
                    _backup_database(
                        feedback_db,
                        output_root=output_root,
                        timestamp_slug=timestamp_slug,
                    )
                )
            for row in stale_rows:
                conn.execute(
                    "DELETE FROM task_audit WHERE domain = ? AND scene_id = ? AND task_id = ?",
                    (str(row["domain"]), str(row["scene_id"]), str(row["task_id"])),
                )

        rows_after = conn.execute(
            "SELECT * FROM task_audit WHERE domain = ? ORDER BY scene_id, task_id",
            (domain,),
        ).fetchall()
        stale_after = [
            row
            for row in rows_after
            if (str(row["domain"]), str(row["scene_id"]), str(row["task_id"])) not in active_keys
        ]

    report: dict[str, Any] = {
        "schema": SCHEMA_ID,
        "generated_at": generated_at,
        "domain": domain,
        "dry_run": not bool(apply),
        "applied": bool(apply),
        "feedback_db": str(feedback_db),
        "review_root": str(review_root),
        "backup_path": backup_path,
        "active_review_task_count": int(len(active_keys)),
        "db_task_audit_rows_before": int(len(rows_before)),
        "db_task_audit_rows_after": int(len(rows_after)),
        "stale_row_count_before": int(len(stale_rows)),
        "stale_row_count_after": int(len(stale_after)),
        "deleted_row_count": int(len(stale_rows) if apply else 0),
        "stale_rows_before_by_scene": _summarize_rows(stale_rows),
        "stale_rows_after_by_scene": _summarize_rows(stale_after),
        "stale_rows_before": [_row_payload(row) for row in stale_rows],
        "stale_rows_after": [_row_payload(row) for row in stale_after],
    }
    json_path, md_path = _write_report_files(report, output_root=output_root, timestamp_slug=timestamp_slug)
    report["report_json"] = str(json_path)
    report["report_md"] = str(md_path)
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--domain", required=True, help="Domain whose stale task_audit rows should be checked")
    parser.add_argument("--feedback-db", type=Path, default=DEFAULT_FEEDBACK_DB)
    parser.add_argument("--review-root", type=Path, default=DEFAULT_REVIEW_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--apply", action="store_true", help="Delete stale rows. Default is dry-run.")
    parser.add_argument("--no-backup", action="store_true", help="Skip SQLite backup when applying cleanup.")
    args = parser.parse_args()

    report = cleanup_retired_task_audit_rows(
        domain=str(args.domain),
        feedback_db=Path(args.feedback_db),
        review_root=Path(args.review_root),
        output_root=Path(args.output_root),
        apply=bool(args.apply),
        backup=not bool(args.no_backup),
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
