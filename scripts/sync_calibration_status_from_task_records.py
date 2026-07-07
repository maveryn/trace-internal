#!/usr/bin/env python3
"""Export the authoritative calibration ledger to legacy status files."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from trace.core.task_review_calibration import (
    CURRENT_CALIBRATION_BASELINE,
    CURRENT_CALIBRATION_RUN_DIR,
    load_calibration_status_records,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-root", default="review/task-reviews")
    parser.add_argument("--status-json", default="review/calibration_sweep_status.json")
    parser.add_argument("--status-md", default="review/calibration_sweep_status.md")
    return parser.parse_args()


def _metric(stats: Mapping[str, Any], key: str) -> str:
    overall = stats.get("overall", {}) if isinstance(stats.get("overall"), Mapping) else {}
    value = overall.get(key)
    return "-" if value is None else f"{float(value):.3f}"


def _cap_rate(stats: Mapping[str, Any]) -> str:
    response_stats = stats.get("response_token_stats", {}) if isinstance(stats.get("response_token_stats"), Mapping) else {}
    value = response_stats.get("cap_rate")
    return "-" if value is None else f"{float(value):.3f}"


def _prompt_count(stats: Mapping[str, Any]) -> str:
    overall = stats.get("overall", {}) if isinstance(stats.get("overall"), Mapping) else {}
    value = overall.get("prompt_count")
    return "-" if value is None else str(int(value))


def _write_markdown(path: Path, *, status: Mapping[str, Any]) -> None:
    rows: list[str] = [
        "# TRACE Calibration Sweep Status",
        "",
        "Derived compatibility view. Do not edit by hand.",
        "",
        f"Source of truth: `{CURRENT_CALIBRATION_RUN_DIR / 'task_status_records.json'}`",
        f"Updated: `{status.get('updated_at', '')}`",
        "",
        "| Domain | Scene | Task | Status | qwen25vl7b H/E/Mean/Cap/Prompts | Source |",
        "|---|---|---|---|---|---|",
    ]
    tasks = status.get("tasks", {}) if isinstance(status.get("tasks"), Mapping) else {}
    for task_id, record in sorted(
        tasks.items(),
        key=lambda item: (str(item[1].get("domain", "")), str(item[1].get("scene_id", "")), str(item[0])),
    ):
        models = record.get("models", {}) if isinstance(record.get("models"), Mapping) else {}
        model_record = models.get("qwen25vl7b", {}) if isinstance(models.get("qwen25vl7b"), Mapping) else {}
        stats = model_record.get("stats", {}) if isinstance(model_record.get("stats"), Mapping) else {}
        metrics = (
            f"{_metric(stats, 'hard_frac')}/"
            f"{_metric(stats, 'easy_frac')}/"
            f"{_metric(stats, 'mean_solve_rate')}/"
            f"{_cap_rate(stats)}/"
            f"{_prompt_count(stats)}"
        )
        source = str(record.get("status_source", "") or record.get("source_of_truth", ""))
        ledger_status = str(record.get("ledger_status", ""))
        if ledger_status and ledger_status != str(record.get("status", "")):
            source = f"{source}<br>ledger_status: `{ledger_status}`" if source else f"ledger_status: `{ledger_status}`"
        rows.append(
            f"| `{record.get('domain', '')}` | `{record.get('scene_id', '')}` | `{task_id}` | "
            f"`{record.get('status', '')}` | {metrics} | {source} |"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def main() -> int:
    args = _parse_args()
    tasks = load_calibration_status_records(
        out_root=Path(args.out_root),
        include_legacy_fallback=False,
    )
    if not tasks:
        raise SystemExit("No authoritative task-status records found")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    status = {
        "schema_version": "calibration_status_compat_from_task_records_v1",
        "updated_at": now,
        "config": {
            "calibration_baseline": CURRENT_CALIBRATION_BASELINE,
            "source_of_truth": str(CURRENT_CALIBRATION_RUN_DIR / "task_status_records.json"),
            "note": "Compatibility export; do not treat as an independent source of truth.",
        },
        "tasks": tasks,
    }
    status_json = Path(args.status_json)
    status_json.parent.mkdir(parents=True, exist_ok=True)
    status_json.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_markdown(Path(args.status_md), status=status)
    print(f"wrote {status_json} and {args.status_md} from {len(tasks)} ledger records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
