#!/usr/bin/env python3
"""Run lightweight answer-distribution checks across TRACE tasks."""

from __future__ import annotations

import argparse
from pathlib import Path
import os
import sys
from typing import Any, Dict, List

from trace.core.answer_distribution import evaluate_answer_distribution
from trace.core.json_io import write_json_file
from trace.core.task_review_sampling import collect_query_id_samples
from trace.tasks import TASK_REGISTRY, create_task


def _resolve_task_ids(raw_tasks: str) -> List[str]:
    """Resolve selected task ids from CLI input."""
    if not str(raw_tasks).strip():
        return sorted(TASK_REGISTRY.keys())
    task_ids = [item.strip() for item in str(raw_tasks).split(",") if item.strip()]
    if not task_ids:
        raise ValueError("--tasks resolved to an empty list")
    unknown = [task_id for task_id in task_ids if task_id not in TASK_REGISTRY]
    if unknown:
        raise ValueError(f"unknown task ids: {', '.join(sorted(unknown))}")
    return sorted(dict.fromkeys(task_ids))


def _parse_cli() -> argparse.Namespace:
    """Parse distribution-check CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Check task answer distributions with lightweight anti-degeneracy rules",
    )
    parser.add_argument("--tasks", default="", help="Comma-separated task ids (default: all registered tasks)")
    parser.add_argument(
        "--count-per-query-id",
        type=int,
        default=100,
        help="Collected samples per query id (default: 100)",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=None,
        help=argparse.SUPPRESS,
    )
    parser.add_argument("--seed", type=int, default=0, help="Base sampling seed")
    parser.add_argument(
        "--max-attempts-per-instance",
        type=int,
        default=200,
        help="Max generation attempts per instance",
    )
    parser.add_argument(
        "--max-total-samples-per-task",
        type=int,
        default=20000,
        help="Safety cap on generated instances per task while collecting per-query-id samples",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=max(1, int(os.cpu_count() or 1)),
        help="Thread workers for sample generation (default: all visible CPUs)",
    )
    parser.add_argument(
        "--out",
        default="tmp/task_answer_distribution",
        help="Output directory for distribution reports",
    )
    parser.add_argument(
        "--allow-fail",
        action="store_true",
        help="Exit with code 0 even when one or more tasks fail checks",
    )
    return parser.parse_args()


def _format_task_distribution_metrics(report: Dict[str, Any]) -> str:
    """Format compact distribution metrics string for terminal output."""
    max_bin_observed = report["checks"]["max_five_bin_frequency"]["observed"]
    max_bin_text = "n/a" if max_bin_observed is None else f"{float(max_bin_observed):.3f}"
    return (
        f"unique={report['unique_answers']}, "
        f"max_answer={report['max_answer_count']}/{report['sample_count']} "
        f"({float(report['max_answer_frequency']):.3f}), "
        f"max_5bin={max_bin_text}"
    )


def _collector(output: Any, instance_seed: int) -> Dict[str, Any]:
    """Collect answer payload for one sampled output."""
    return {
        "instance_seed": int(instance_seed),
        "answer_type": str(output.answer_gt.type),
        "answer_value": output.answer_gt.value,
    }


def _empty_distribution_report() -> Dict[str, Any]:
    """Build one empty fallback distribution report."""
    return {
        "sample_count": 0,
        "unique_answers": 0,
        "max_answer_count": 0,
        "max_answer_frequency": 0.0,
        "checks": {
            "min_unique_answers": {"pass": False},
            "max_answer_frequency": {"pass": False},
            "max_five_bin_frequency": {"pass": None, "observed": None, "status": "not_reported_no_samples"},
        },
        "pass": False,
    }


def main() -> int:
    """Entry point for task answer-distribution checks."""
    args = _parse_cli()
    if args.count is not None:
        args.count_per_query_id = int(args.count)
    if int(args.count_per_query_id) <= 0:
        raise ValueError("--count-per-query-id must be > 0")
    if int(args.max_attempts_per_instance) <= 0:
        raise ValueError("--max-attempts-per-instance must be > 0")
    if int(args.max_total_samples_per_task) <= 0:
        raise ValueError("--max-total-samples-per-task must be > 0")
    if int(args.workers) <= 0:
        raise ValueError("--workers must be > 0")

    task_ids = _resolve_task_ids(str(args.tasks))
    out_root = Path(str(args.out)).resolve()
    out_root.mkdir(parents=True, exist_ok=True)

    report: Dict[str, Any] = {
        "config": {
            "count_per_query_id": int(args.count_per_query_id),
            "seed": int(args.seed),
            "max_attempts_per_instance": int(args.max_attempts_per_instance),
            "max_total_samples_per_task": int(args.max_total_samples_per_task),
            "workers": int(args.workers),
            "checks": {
                "min_unique_answers": 5,
                "max_answer_frequency": 1.0 / 3.0,
                "numeric_bin_summary": "reported_only_five_equal_width_bins",
            },
        },
        "tasks": [],
    }

    failed: List[str] = []

    for task_id in task_ids:
        task_instance = create_task(str(task_id))
        collected = collect_query_id_samples(
            task_id=str(task_id),
            target_count_per_query_id=int(args.count_per_query_id),
            seed=int(args.seed),
            max_attempts_per_instance=int(args.max_attempts_per_instance),
            max_total_samples_per_task=int(args.max_total_samples_per_task),
            workers=int(args.workers),
            collector=_collector,
        )

        expected_query_ids = list(collected.get("expected_query_ids", []))
        samples_by_query_id = dict(collected.get("samples_by_query_id", {}))
        if not expected_query_ids:
            expected_query_ids = sorted(samples_by_query_id.keys())

        variant_reports = {
            str(variant): evaluate_answer_distribution(list(samples_by_query_id.get(str(variant), [])))
            for variant in expected_query_ids
            if samples_by_query_id.get(str(variant))
        }

        combined_rows: List[Dict[str, Any]] = []
        for variant in expected_query_ids:
            combined_rows.extend(list(samples_by_query_id.get(str(variant), [])))

        overall_report = (
            evaluate_answer_distribution(combined_rows)
            if combined_rows
            else _empty_distribution_report()
        )

        failing_query_ids = [
            str(query_id)
            for query_id, variant_report in variant_reports.items()
            if not bool(variant_report["pass"])
        ]
        incomplete_query_ids = list(collected.get("incomplete_query_ids", []))
        no_samples_collected = not bool(combined_rows)
        task_pass = bool((not failing_query_ids) and (not incomplete_query_ids) and (not no_samples_collected))

        task_report: Dict[str, Any] = dict(overall_report)
        task_report["task_id"] = str(task_id)
        task_report["domain"] = str(getattr(task_instance, "domain", ""))
        task_report["task_group"] = str(getattr(task_instance, "task_group", ""))
        task_report["target_count_per_query_id"] = int(args.count_per_query_id)
        task_report["total_generated"] = int(collected.get("total_generated", 0))
        task_report["expected_query_ids"] = list(expected_query_ids)
        task_report["generated_query_id_counts"] = dict(collected.get("generated_query_id_counts", {}))
        task_report["collected_query_id_counts"] = dict(collected.get("collected_query_id_counts", {}))
        task_report["generation_error_counts"] = dict(collected.get("generation_error_counts", {}))
        task_report["overall"] = overall_report
        task_report["per_query_id"] = variant_reports
        task_report["failed_query_ids"] = list(failing_query_ids)
        task_report["incomplete_query_ids"] = list(incomplete_query_ids)
        task_report["no_samples_collected"] = bool(no_samples_collected)
        task_report["pass"] = bool(task_pass)
        report["tasks"].append(task_report)

        status = "PASS" if bool(task_pass) else "FAIL"
        variant_count = len(variant_reports)
        print(
            f"[{status}] {task_id}: variants={variant_count}, generated={task_report['total_generated']}, "
            f"overall({_format_task_distribution_metrics(overall_report)})"
        )
        for query_id, variant_report in variant_reports.items():
            label = str(query_id) if str(query_id).strip() else "<default>"
            variant_status = "PASS" if bool(variant_report["pass"]) else "FAIL"
            print(f"    - [{variant_status}] {label}: {_format_task_distribution_metrics(variant_report)}")
        if incomplete_query_ids:
            print(f"    - [FAIL] incomplete_query_ids: {', '.join(incomplete_query_ids)}")
        if no_samples_collected:
            print("    - [FAIL] no_samples_collected")

        if not bool(task_pass):
            failed.append(str(task_id))

    total = len(report["tasks"])
    failed_count = len(failed)
    report["summary"] = {
        "total_tasks": int(total),
        "passed_tasks": int(total - failed_count),
        "failed_tasks": int(failed_count),
        "failed_task_ids": sorted(failed),
        "failed_query_id_map": {
            str(task_report["task_id"]): list(task_report.get("failed_query_ids", []))
            for task_report in report["tasks"]
            if not bool(task_report.get("pass"))
        },
        "incomplete_query_id_map": {
            str(task_report["task_id"]): list(task_report.get("incomplete_query_ids", []))
            for task_report in report["tasks"]
            if task_report.get("incomplete_query_ids")
        },
        "no_samples_task_ids": sorted(
            str(task_report["task_id"])
            for task_report in report["tasks"]
            if bool(task_report.get("no_samples_collected", False))
        ),
    }

    write_json_file(out_root / "task_answer_distribution_report.json", report)
    print(f"[done] wrote report: {out_root / 'task_answer_distribution_report.json'}")
    print(
        f"[summary] passed={report['summary']['passed_tasks']}/{report['summary']['total_tasks']}, "
        f"failed={report['summary']['failed_tasks']}"
    )

    if failed and not bool(args.allow_fail):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
