#!/usr/bin/env python3
"""Invalidate human supervision-policy approvals without changing other gates."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sqlite3
import sys
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from trace.core.source_layout_policy import parse_public_task_id  # noqa: E402


DEFAULT_ACTIVE_INVENTORY = Path("docs/ACTIVE_TASK_INVENTORY.md")
DEFAULT_FEEDBACK_DB = Path("review/feedback/review_feedback.sqlite")
DEFAULT_OUTPUT_ROOT = Path("review/supervision-policy")
DEFAULT_UPDATED_BY = "task_supervision_policy_audit"
REPORT_SCHEMA = "trace_task_supervision_review_reset_v1"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _active_task_ids(path: Path, domains: Iterable[str]) -> tuple[str, ...]:
    requested_domains = {str(domain).strip() for domain in domains if str(domain).strip()}
    task_ids = re.findall(r"^- `(task_[^`]+)`$", path.read_text(encoding="utf-8"), re.MULTILINE)
    if requested_domains:
        task_ids = [
            task_id
            for task_id in task_ids
            if parse_public_task_id(task_id).domain in requested_domains
        ]
    return tuple(sorted(set(task_ids)))


def _backup_database(source_path: Path, destination_path: Path) -> None:
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(source_path, timeout=30.0) as source, sqlite3.connect(
        destination_path, timeout=30.0
    ) as destination:
        source.execute("PRAGMA busy_timeout=30000")
        source.execute("PRAGMA wal_checkpoint(FULL)")
        source.backup(destination)


def reset_supervision_reviews(
    *,
    active_inventory: Path = DEFAULT_ACTIVE_INVENTORY,
    feedback_db: Path = DEFAULT_FEEDBACK_DB,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    domains: Iterable[str] = (),
    apply: bool = False,
    backup: bool = True,
    updated_by: str = DEFAULT_UPDATED_BY,
) -> dict[str, Any]:
    """Return reset results and optionally clear active supervision approvals."""

    active_inventory = Path(active_inventory)
    feedback_db = Path(feedback_db)
    output_root = Path(output_root)
    if not feedback_db.exists():
        raise FileNotFoundError(f"feedback DB does not exist: {feedback_db}")

    task_ids = _active_task_ids(active_inventory, domains)
    generated_at = _now()
    placeholders = ",".join("?" for _ in task_ids)
    with sqlite3.connect(feedback_db, timeout=30.0) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout=30000")
        rows = (
            conn.execute(
                f"SELECT * FROM task_audit WHERE task_id IN ({placeholders}) ORDER BY task_id",
                task_ids,
            ).fetchall()
            if task_ids
            else []
        )
        rows_by_task = {str(row["task_id"]): row for row in rows}
        approved = [
            task_id
            for task_id in task_ids
            if task_id in rows_by_task
            and int(rows_by_task[task_id]["supervision_review_pass"] or 0)
        ]
        missing = [task_id for task_id in task_ids if task_id not in rows_by_task]

        backup_path = ""
        if apply and approved:
            timestamp = generated_at.replace("+00:00", "Z").replace(":", "").replace("-", "")
            if backup:
                destination = output_root / f"{feedback_db.name}.supervision_reset_{timestamp}.bak"
                _backup_database(feedback_db, destination)
                backup_path = str(destination)
            conn.executemany(
                """
                UPDATE task_audit
                SET supervision_review_pass = 0,
                    updated_at = ?,
                    updated_by = ?
                WHERE task_id = ? AND supervision_review_pass != 0
                """,
                [(generated_at, str(updated_by), task_id) for task_id in approved],
            )

    by_domain = Counter(parse_public_task_id(task_id).domain for task_id in approved)
    return {
        "schema": REPORT_SCHEMA,
        "generated_at": generated_at,
        "applied": bool(apply),
        "active_task_count": len(task_ids),
        "reset_count": len(approved),
        "already_unchecked_count": len(task_ids) - len(approved) - len(missing),
        "missing_audit_row_count": len(missing),
        "reset_count_by_domain": dict(sorted(by_domain.items())),
        "reset_task_ids": approved,
        "missing_task_ids": missing,
        "backup_path": backup_path,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--active-inventory", type=Path, default=DEFAULT_ACTIVE_INVENTORY)
    parser.add_argument("--feedback-db", type=Path, default=DEFAULT_FEEDBACK_DB)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--domain", action="append", default=[])
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--no-backup", action="store_true")
    parser.add_argument("--updated-by", default=DEFAULT_UPDATED_BY)
    args = parser.parse_args()

    report = reset_supervision_reviews(
        active_inventory=args.active_inventory,
        feedback_db=args.feedback_db,
        output_root=args.output_root,
        domains=args.domain,
        apply=bool(args.apply),
        backup=not bool(args.no_backup),
        updated_by=str(args.updated_by),
    )
    args.output_root.mkdir(parents=True, exist_ok=True)
    suffix = "applied" if args.apply else "dry_run"
    report_path = args.output_root / f"task_supervision_review_reset_{suffix}.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    print(f"[done] wrote {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
