#!/usr/bin/env python3
"""Validate answer-distribution health on an exact exported RLVR probe parquet."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Dict, Iterable, List, Mapping, Sequence

import pyarrow.parquet as pq

from trace.core.answer_distribution import evaluate_answer_distribution
from trace.core.json_io import write_json_file
from trace.core.trace_store import read_trace_shard


def _parse_cli() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check answer-distribution health on one or more exact RLVR probe parquets."
    )
    parser.add_argument(
        "--parquet",
        required=True,
        action="append",
        help="Path to an RLVR parquet to validate. Repeat to validate a cumulative sample.",
    )
    parser.add_argument(
        "--dataset-root",
        action="append",
        default=[],
        help="Optional TRACE dataset root used to resolve trace_ref -> query_variant. Repeat in parquet order.",
    )
    parser.add_argument(
        "--out",
        default="",
        help="Optional JSON report path (default: <parquet>.distribution_report.json)",
    )
    parser.add_argument(
        "--min-unique-answers",
        type=int,
        default=5,
        help="Minimum unique answers threshold",
    )
    parser.add_argument(
        "--max-answer-frequency",
        type=float,
        default=1.0 / 3.0,
        help="Maximum top-answer frequency threshold",
    )
    parser.add_argument(
        "--allow-fail",
        action="store_true",
        help="Exit 0 even when one or more checks fail",
    )
    return parser.parse_args()


def _json_load_maybe(value: Any) -> Any:
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return value
        return json.loads(text)
    return value


def _empty_distribution_report() -> Dict[str, Any]:
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


def _load_rows(parquet_path: Path, *, dataset_root: Path | None = None) -> List[Dict[str, Any]]:
    table = pq.read_table(parquet_path)
    data = table.to_pylist()
    rows: List[Dict[str, Any]] = []
    for row in data:
        parsed = dict(row)
        parsed["answer_gt"] = _json_load_maybe(parsed.get("answer_gt"))
        parsed["trace_ref"] = _json_load_maybe(parsed.get("trace_ref"))
        if dataset_root is not None:
            parsed["_dataset_root"] = str(dataset_root)
        rows.append(parsed)
    return rows


def _answer_rows(rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    collected: List[Dict[str, Any]] = []
    for row in rows:
        answer_gt = row.get("answer_gt")
        if not isinstance(answer_gt, Mapping):
            raise ValueError("row answer_gt is missing or invalid")
        collected.append(
            {
                "answer_type": str(answer_gt.get("type", "")),
                "answer_value": answer_gt.get("value"),
            }
        )
    return collected


def _load_trace_record(
    *,
    dataset_root: Path,
    trace_ref: Mapping[str, Any],
    cache: Dict[tuple[str, str], List[Dict[str, Any]]],
) -> Dict[str, Any]:
    shard_id = str(trace_ref.get("shard_id", "")).strip()
    line_index = int(trace_ref.get("line_index", -1))
    if not shard_id:
        raise ValueError("trace_ref shard_id is missing")
    if line_index < 0:
        raise ValueError("trace_ref line_index is invalid")
    cache_key = (str(dataset_root.resolve()), str(shard_id))
    records = cache.get(cache_key)
    if records is None:
        records = read_trace_shard(dataset_root / "traces" / shard_id)
        cache[cache_key] = records
    if line_index >= len(records):
        raise ValueError("trace_ref line_index is out of range")
    return dict(records[line_index])


def _resolve_variant_fields(
    *,
    rows: Sequence[Dict[str, Any]],
) -> tuple[Dict[str, Dict[str, List[Dict[str, Any]]]], Dict[str, List[str]]]:
    rows_by_query_variant: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
    expected_variants_by_task: Dict[str, set[str]] = {}
    trace_cache: Dict[tuple[str, str], List[Dict[str, Any]]] = {}

    for row in rows:
        task_id = str(row.get("task", "")).strip()
        if not task_id:
            continue
        trace_ref = row.get("trace_ref")
        if not isinstance(trace_ref, Mapping):
            continue
        dataset_root_text = str(row.get("_dataset_root", "")).strip()
        if not dataset_root_text:
            continue
        dataset_root = Path(dataset_root_text)
        trace_record = _load_trace_record(dataset_root=dataset_root, trace_ref=trace_ref, cache=trace_cache)
        execution_trace = trace_record.get("execution_trace", {})
        if not isinstance(execution_trace, Mapping):
            execution_trace = {}
        query_id = str(execution_trace.get("query_id", "") or "").strip()
        query_variant = str(execution_trace.get("query_variant", "") or "").strip()
        query_label = query_id or query_variant
        probabilities = execution_trace.get("query_variant_probabilities", {})
        if isinstance(probabilities, Mapping):
            expected_variants_by_task.setdefault(task_id, set()).update(
                str(key) for key in probabilities.keys() if str(key).strip()
            )
        rows_by_query_variant.setdefault(task_id, {}).setdefault(query_label, []).append(row)

    expected_lists = {
        task_id: sorted(variants)
        for task_id, variants in expected_variants_by_task.items()
    }
    return rows_by_query_variant, expected_lists


def _format_metrics(report: Mapping[str, Any]) -> str:
    return (
        f"unique={int(report['unique_answers'])}, "
        f"max_answer={int(report['max_answer_count'])}/{int(report['sample_count'])} "
        f"({float(report['max_answer_frequency']):.3f})"
    )


def _task_report(
    *,
    task_id: str,
    rows: Sequence[Dict[str, Any]],
    rows_by_variant: Mapping[str, Sequence[Dict[str, Any]]],
    expected_variants: Sequence[str],
    min_unique_answers: int,
    max_answer_frequency: float,
) -> Dict[str, Any]:
    overall = evaluate_answer_distribution(
        _answer_rows(rows),
        min_unique_answers=min_unique_answers,
        max_answer_frequency=max_answer_frequency,
    )

    per_query_variant: Dict[str, Dict[str, Any]] = {}
    missing_variants: List[str] = []
    expected = list(expected_variants) if expected_variants else sorted(rows_by_variant.keys())
    if not expected and rows_by_variant:
        expected = sorted(rows_by_variant.keys())

    for query_variant in expected:
        variant_rows = list(rows_by_variant.get(str(query_variant), []))
        if variant_rows:
            per_query_variant[str(query_variant)] = evaluate_answer_distribution(
                _answer_rows(variant_rows),
                min_unique_answers=min_unique_answers,
                max_answer_frequency=max_answer_frequency,
            )
        else:
            per_query_variant[str(query_variant)] = _empty_distribution_report()
            missing_variants.append(str(query_variant))

    failing_variants = [
        str(query_variant)
        for query_variant, report in per_query_variant.items()
        if not bool(report.get("pass"))
    ]

    task_pass = bool(overall["pass"] and not failing_variants and not missing_variants)
    return {
        "task_id": str(task_id),
        "sample_count": int(len(rows)),
        "overall": overall,
        "expected_variants": list(expected),
        "observed_variant_counts": {
            str(query_variant): int(len(rows_by_variant.get(str(query_variant), [])))
            for query_variant in sorted(rows_by_variant.keys())
        },
        "per_query_variant": per_query_variant,
        "missing_variants": missing_variants,
        "failed_variants": failing_variants,
        "pass": task_pass,
    }


def main() -> int:
    args = _parse_cli()
    parquet_paths = [Path(str(value)).resolve() for value in args.parquet]
    for parquet_path in parquet_paths:
        if not parquet_path.exists():
            raise FileNotFoundError(f"parquet not found: {parquet_path}")

    raw_dataset_roots = [str(value).strip() for value in args.dataset_root if str(value).strip()]
    if raw_dataset_roots and len(raw_dataset_roots) != len(parquet_paths):
        raise ValueError("--dataset-root must be repeated once per --parquet when provided")
    dataset_roots = [Path(value).resolve() for value in raw_dataset_roots]
    rows: List[Dict[str, Any]] = []
    for index, parquet_path in enumerate(parquet_paths):
        dataset_root = dataset_roots[index] if dataset_roots else None
        rows.extend(_load_rows(parquet_path, dataset_root=dataset_root))
    if not rows:
        raise ValueError("probe parquet is empty")

    rows_by_task: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        task_id = str(row.get("task", "")).strip()
        rows_by_task.setdefault(task_id, []).append(row)

    rows_by_query_variant: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
    expected_variants_by_task: Dict[str, List[str]] = {}
    if dataset_roots:
        rows_by_query_variant, expected_variants_by_task = _resolve_variant_fields(rows=rows)

    report: Dict[str, Any] = {
        "config": {
            "parquets": [str(path) for path in parquet_paths],
            "dataset_roots": [str(path) for path in dataset_roots],
            "min_unique_answers": int(args.min_unique_answers),
            "max_answer_frequency": float(args.max_answer_frequency),
        },
        "tasks": [],
    }

    failed_tasks: List[str] = []
    for task_id in sorted(rows_by_task.keys()):
        task_rows = list(rows_by_task.get(task_id, []))
        variant_rows = rows_by_query_variant.get(task_id, {})
        task_report = _task_report(
            task_id=task_id,
            rows=task_rows,
            rows_by_variant=variant_rows,
            expected_variants=expected_variants_by_task.get(task_id, []),
            min_unique_answers=int(args.min_unique_answers),
            max_answer_frequency=float(args.max_answer_frequency),
        )
        report["tasks"].append(task_report)

        status = "PASS" if bool(task_report["pass"]) else "FAIL"
        print(f"[{status}] {task_id}: overall({_format_metrics(task_report['overall'])})")
        if task_report["per_query_variant"]:
            for query_variant, variant_report in sorted(task_report["per_query_variant"].items()):
                label = str(query_variant).strip() or "<default>"
                variant_status = "PASS" if bool(variant_report.get("pass")) else "FAIL"
                print(f"    - [{variant_status}] {label}: {_format_metrics(variant_report)}")
        if task_report["missing_variants"]:
            print(f"    - [FAIL] missing_variants: {', '.join(task_report['missing_variants'])}")

        if not bool(task_report["pass"]):
            failed_tasks.append(str(task_id))

    report["summary"] = {
        "total_tasks": int(len(report["tasks"])),
        "passed_tasks": int(len(report["tasks"]) - len(failed_tasks)),
        "failed_tasks": int(len(failed_tasks)),
        "failed_task_ids": sorted(failed_tasks),
    }

    out_path = (
        Path(str(args.out)).resolve()
        if str(args.out).strip()
        else parquet_paths[0].with_suffix(parquet_paths[0].suffix + ".distribution_report.json")
    )
    write_json_file(out_path, report)
    print(f"[done] wrote report: {out_path}")

    if failed_tasks and not bool(args.allow_fail):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
