#!/usr/bin/env python3
"""Reset manual annotation audit gates after scalar annotation rollout."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any, Iterable

from scripts.inventory_scalar_annotations import TaskRef, parse_active_inventory
from trace.core.scene_package_migration import SCENE_PACKAGE_REVIEW_CANDIDATE_SCENES


DEFAULT_ACTIVE_INVENTORY = Path("docs/ACTIVE_TASK_INVENTORY.md")
DEFAULT_FEEDBACK_DB = Path("review/feedback/review_feedback.sqlite")
DEFAULT_OUTPUT_ROOT = Path("review/scalar-annotation")
DEFAULT_UPDATED_BY = "scalar_annotation_stage4"
SCHEMA_ID = "trace_scalar_annotation_review_reset_v0"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _review_candidate_tasks(active_inventory: Path) -> list[TaskRef]:
    records = parse_active_inventory(active_inventory.read_text(encoding="utf-8"))
    return [
        record
        for record in records
        if record.scene_id in SCENE_PACKAGE_REVIEW_CANDIDATE_SCENES.get(record.domain, frozenset())
    ]


def _connect_existing_feedback_db(feedback_db: Path) -> sqlite3.Connection:
    if not feedback_db.exists():
        raise FileNotFoundError(f"feedback DB does not exist: {feedback_db}")
    conn = sqlite3.connect(feedback_db, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def _load_task_audit_rows(conn: sqlite3.Connection) -> dict[tuple[str, str, str], sqlite3.Row]:
    rows = conn.execute("SELECT * FROM task_audit ORDER BY domain, scene_id, task_id").fetchall()
    return {
        (str(row["domain"]), str(row["scene_id"]), str(row["task_id"])): row
        for row in rows
    }


def _row_payload(row: sqlite3.Row) -> dict[str, Any]:
    return {str(key): row[key] for key in row.keys()}


def _backup_database(feedback_db: Path, *, output_root: Path, timestamp_slug: str) -> Path:
    output_root.mkdir(parents=True, exist_ok=True)
    backup_path = output_root / f"{feedback_db.name}.stage4_annotation_reset_{timestamp_slug}.bak"
    with sqlite3.connect(feedback_db, timeout=30.0) as source, sqlite3.connect(backup_path) as backup:
        source.execute("PRAGMA busy_timeout=30000")
        source.execute("PRAGMA wal_checkpoint(FULL)")
        source.backup(backup)
    return backup_path


def _summarize_by_domain(records: Iterable[TaskRef]) -> dict[str, int]:
    counts = Counter(record.domain for record in records)
    return {str(domain): int(counts[domain]) for domain in sorted(counts)}


def reset_annotation_reviews(
    *,
    active_inventory: Path = DEFAULT_ACTIVE_INVENTORY,
    feedback_db: Path = DEFAULT_FEEDBACK_DB,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    apply: bool = False,
    backup: bool = True,
    updated_by: str = DEFAULT_UPDATED_BY,
) -> dict[str, Any]:
    """Reset annotation_pass for review-candidate tasks, preserving other gates."""

    active_inventory = Path(active_inventory)
    feedback_db = Path(feedback_db)
    output_root = Path(output_root)
    generated_at = _now()
    timestamp_slug = generated_at.replace(":", "").replace("+", "Z").replace("-", "").replace(".", "")
    targets = _review_candidate_tasks(active_inventory)
    target_keys = {(record.domain, record.scene_id, record.task_id) for record in targets}

    with _connect_existing_feedback_db(feedback_db) as conn:
        audit_rows = _load_task_audit_rows(conn)
        changed: list[dict[str, Any]] = []
        unchanged_false: list[dict[str, str]] = []
        missing_rows: list[dict[str, str]] = []
        non_target_true = 0

        for record in targets:
            key = (record.domain, record.scene_id, record.task_id)
            row = audit_rows.get(key)
            if row is None:
                missing_rows.append(record.__dict__)
                continue
            if int(row["annotation_pass"] or 0):
                changed.append(
                    {
                        "domain": record.domain,
                        "scene_id": record.scene_id,
                        "task_id": record.task_id,
                        "previous": _row_payload(row),
                    }
                )
            else:
                unchanged_false.append(record.__dict__)

        for key, row in audit_rows.items():
            if key not in target_keys and int(row["annotation_pass"] or 0):
                non_target_true += 1

        backup_path = ""
        if apply and changed:
            if backup:
                backup_path = str(_backup_database(feedback_db, output_root=output_root, timestamp_slug=timestamp_slug))
            update_time = _now()
            for item in changed:
                conn.execute(
                    """
                    UPDATE task_audit
                    SET annotation_pass = 0,
                        updated_at = ?,
                        updated_by = ?
                    WHERE domain = ? AND scene_id = ? AND task_id = ? AND annotation_pass != 0
                    """,
                    (
                        update_time,
                        str(updated_by),
                        str(item["domain"]),
                        str(item["scene_id"]),
                        str(item["task_id"]),
                    ),
                )

    by_domain = defaultdict(Counter)
    for item in changed:
        by_domain[str(item["domain"])]["reset"] += 1
    for item in missing_rows:
        by_domain[str(item["domain"])]["no_row"] += 1
    for item in unchanged_false:
        by_domain[str(item["domain"])]["already_false"] += 1

    report = {
        "schema": SCHEMA_ID,
        "generated_at": generated_at,
        "dry_run": not bool(apply),
        "applied": bool(apply),
        "active_inventory": str(active_inventory),
        "feedback_db": str(feedback_db),
        "backup_path": backup_path,
        "updated_by": str(updated_by),
        "target_task_count": len(targets),
        "target_task_count_by_domain": _summarize_by_domain(targets),
        "reset_count": len(changed),
        "already_false_count": len(unchanged_false),
        "missing_row_count": len(missing_rows),
        "non_target_annotation_true_count": int(non_target_true),
        "by_domain": {
            str(domain): {str(key): int(value) for key, value in counter.items()}
            for domain, counter in sorted(by_domain.items())
        },
        "reset_tasks": [
            {
                "domain": str(item["domain"]),
                "scene_id": str(item["scene_id"]),
                "task_id": str(item["task_id"]),
                "preserved_gates": {
                    "prompt_pass": int(item["previous"]["prompt_pass"] or 0),
                    "image_pass": int(item["previous"]["image_pass"] or 0),
                    "distribution_pass": int(item["previous"]["distribution_pass"] or 0),
                    "code_review_pass": int(item["previous"]["code_review_pass"] or 0),
                    "taxonomy_review_pass": int(item["previous"]["taxonomy_review_pass"] or 0),
                    "solve_rate_pass": int(item["previous"]["solve_rate_pass"] or 0),
                },
            }
            for item in changed
        ],
        "missing_row_tasks": list(missing_rows),
    }
    return report


def write_report(report: dict[str, Any], *, output_root: Path) -> tuple[Path, Path]:
    output_root.mkdir(parents=True, exist_ok=True)
    stem = "stage4_review_reset_applied" if bool(report.get("applied")) else "stage4_review_reset_dry_run"
    json_path = output_root / f"{stem}.json"
    md_path = output_root / f"{stem}.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# Scalar Annotation Stage 4 Review Reset",
        "",
        f"- Generated at: `{report['generated_at']}`",
        f"- Dry run: `{bool(report['dry_run'])}`",
        f"- Applied: `{bool(report['applied'])}`",
        f"- Target tasks: `{int(report['target_task_count'])}`",
        f"- Reset tasks: `{int(report['reset_count'])}`",
        f"- Already unchecked: `{int(report['already_false_count'])}`",
        f"- Missing audit rows: `{int(report['missing_row_count'])}`",
        f"- Non-target annotation-checked rows left untouched: `{int(report['non_target_annotation_true_count'])}`",
    ]
    if report.get("backup_path"):
        lines.append(f"- Backup: `{report['backup_path']}`")
    lines.extend(["", "## By Domain", "", "| Domain | Reset | Already unchecked | Missing row |", "| --- | ---: | ---: | ---: |"])
    for domain, values in report.get("by_domain", {}).items():
        lines.append(
            f"| {domain} | {int(values.get('reset', 0))} | "
            f"{int(values.get('already_false', 0))} | {int(values.get('no_row', 0))} |"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Reset scalar annotation manual review state for migrated tasks")
    parser.add_argument("--active-inventory", type=Path, default=DEFAULT_ACTIVE_INVENTORY)
    parser.add_argument("--feedback-db", type=Path, default=DEFAULT_FEEDBACK_DB)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--apply", action="store_true", help="apply the reset; default is dry-run")
    parser.add_argument("--no-backup", action="store_true", help="skip SQLite backup when applying")
    parser.add_argument("--updated-by", default=DEFAULT_UPDATED_BY)
    args = parser.parse_args()

    report = reset_annotation_reviews(
        active_inventory=args.active_inventory,
        feedback_db=args.feedback_db,
        output_root=args.output_root,
        apply=bool(args.apply),
        backup=not bool(args.no_backup),
        updated_by=str(args.updated_by),
    )
    json_path, md_path = write_report(report, output_root=args.output_root)
    print(
        f"{'applied' if args.apply else 'dry-run'}: "
        f"targets={report['target_task_count']} reset={report['reset_count']} "
        f"already_false={report['already_false_count']} missing_rows={report['missing_row_count']}"
    )
    print(f"wrote {json_path}")
    print(f"wrote {md_path}")
    if report.get("backup_path"):
        print(f"backup {report['backup_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
