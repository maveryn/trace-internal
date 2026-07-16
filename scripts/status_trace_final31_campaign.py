#!/usr/bin/env python3
"""Report durable Final31 generation, scoring, archive, and GPU progress."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import time
from pathlib import Path
from typing import Any

from benchmark_queue_lib import TRACE_FINAL31_BENCHMARKS, run_dir, score_path, spec_by_key


DEFAULT_MODELS = (
    "qwen25vl7b-base",
    "trace-qwen25vl7b-answer-step500-rerun-20260715",
    "vero-qwen25-7b",
)


def _manifest_rows(path: Path) -> dict[str, int]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    view = payload.get("dataset_views", {}).get("all31")
    if view != list(TRACE_FINAL31_BENCHMARKS):
        raise ValueError("dataset manifest all31 view does not match TRACE_FINAL31_BENCHMARKS")
    datasets = payload.get("datasets") or {}
    rows = {key: int((datasets.get(key) or {}).get("rows", -1)) for key in view}
    invalid = {key: value for key, value in rows.items() if value <= 0}
    if invalid:
        raise ValueError(f"dataset manifest has invalid Final31 row counts: {invalid}")
    return rows


def _row_result_progress(path: Path, *, recent_after: float) -> tuple[int, int]:
    count = 0
    recent = 0
    try:
        entries = os.scandir(path)
    except FileNotFoundError:
        return 0, 0
    with entries:
        for entry in entries:
            if not entry.name.endswith(".json") or not entry.is_file(follow_symlinks=False):
                continue
            count += 1
            try:
                if entry.stat(follow_symlinks=False).st_mtime >= recent_after:
                    recent += 1
            except FileNotFoundError:
                continue
    return count, recent


def _score_complete(path: Path, expected_rows: int) -> bool:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        score = float(payload["score"])
        rows = int(payload["rows"])
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        return False
    return score == score and rows == expected_rows


def _archive_status(spool_root: Path) -> dict[str, int]:
    ledger = spool_root / "ledger.sqlite3"
    result = {"descriptors": 0, "discovered": 0, "built": 0, "uploaded": 0, "failed": 0}
    ready = spool_root / "ready"
    if ready.is_dir():
        result["descriptors"] = sum(1 for _ in ready.glob("*.ready.json"))
    if not ledger.is_file():
        return result
    try:
        with sqlite3.connect(ledger) as connection:
            for status, count in connection.execute(
                "SELECT status, COUNT(*) FROM slices GROUP BY status"
            ):
                if status in result:
                    result[str(status)] = int(count)
    except sqlite3.Error:
        result["failed"] += 1
    return result


def _gpu_status() -> list[dict[str, Any]]:
    command = [
        "nvidia-smi",
        "--query-gpu=index,utilization.gpu,memory.used,memory.total",
        "--format=csv,noheader,nounits",
    ]
    try:
        output = subprocess.run(command, check=True, capture_output=True, text=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return []
    records = []
    for line in output.splitlines():
        fields = [field.strip() for field in line.split(",")]
        if len(fields) != 4:
            continue
        records.append(
            {
                "index": int(fields[0]),
                "utilization": int(fields[1]),
                "memory_used_mib": int(fields[2]),
                "memory_total_mib": int(fields[3]),
            }
        )
    return records


def collect_status(args: argparse.Namespace) -> dict[str, Any]:
    expected_by_benchmark = _manifest_rows(args.dataset_manifest)
    expected_per_model_seed = sum(expected_by_benchmark.values())
    recent_window = max(30.0, float(args.rate_window_seconds))
    recent_after = time.time() - recent_window
    records: list[dict[str, Any]] = []
    recent_rows = 0
    durable_rows = 0
    score_slices = 0
    for seed in args.seeds:
        run_root = args.campaign_root / f"seed_{seed}" / "runs"
        benchmark_root = args.score_root / f"seed_{seed}" / "benchmark"
        for model_slug in args.model_slugs:
            model_rows = 0
            model_recent = 0
            model_scores = 0
            complete_benchmarks = 0
            for key in TRACE_FINAL31_BENCHMARKS:
                spec = spec_by_key(key)
                output_dir = run_dir(spec, model_slug, run_root)
                summary_path = output_dir / "generation_summary.json"
                expected_rows = expected_by_benchmark[key]
                rows, recent = _row_result_progress(
                    output_dir / "api_row_results", recent_after=recent_after
                )
                if summary_path.is_file():
                    try:
                        summary = json.loads(summary_path.read_text(encoding="utf-8"))
                        if int(summary["rows"]) == int(summary["expected_rows"]) == expected_rows:
                            rows = expected_rows
                            complete_benchmarks += 1
                    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
                        pass
                rows = min(rows, expected_rows)
                model_rows += rows
                model_recent += recent
                if _score_complete(score_path(spec, model_slug, benchmark_root), expected_rows):
                    model_scores += 1
            durable_rows += model_rows
            recent_rows += model_recent
            score_slices += model_scores
            records.append(
                {
                    "seed": seed,
                    "model_slug": model_slug,
                    "durable_rows": model_rows,
                    "expected_rows": expected_per_model_seed,
                    "generation_benchmarks": complete_benchmarks,
                    "expected_benchmarks": len(TRACE_FINAL31_BENCHMARKS),
                    "score_slices": model_scores,
                    "expected_score_slices": len(TRACE_FINAL31_BENCHMARKS),
                }
            )
    expected_rows_total = expected_per_model_seed * len(args.seeds) * len(args.model_slugs)
    expected_score_slices = len(TRACE_FINAL31_BENCHMARKS) * len(args.seeds) * len(args.model_slugs)
    rate = recent_rows / recent_window
    remaining = max(0, expected_rows_total - durable_rows)
    eta_seconds = remaining / rate if rate > 0 and remaining else (0.0 if not remaining else None)
    gpus = _gpu_status() if args.gpu else []
    warnings: list[str] = []
    if remaining and gpus and max(item["utilization"] for item in gpus) < args.low_gpu_threshold:
        warnings.append(
            f"generation incomplete while every GPU is below {args.low_gpu_threshold}% utilization"
        )
    return {
        "campaign_root": str(args.campaign_root),
        "score_root": str(args.score_root),
        "models": list(args.model_slugs),
        "seeds": list(args.seeds),
        "benchmarks": len(TRACE_FINAL31_BENCHMARKS),
        "durable_rows": durable_rows,
        "expected_rows": expected_rows_total,
        "recent_rows": recent_rows,
        "recent_rows_per_second": rate,
        "generation_eta_seconds": eta_seconds,
        "score_slices": score_slices,
        "expected_score_slices": expected_score_slices,
        "records": records,
        "archive": _archive_status(args.archive_spool_root),
        "gpus": gpus,
        "warnings": warnings,
        "complete": durable_rows == expected_rows_total and score_slices == expected_score_slices,
    }


def _duration(value: float | None) -> str:
    if value is None:
        return "unknown"
    seconds = max(0, int(value))
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def print_status(report: dict[str, Any]) -> None:
    print(
        "[final31-status] "
        f"generation={report['durable_rows']}/{report['expected_rows']} "
        f"rate={report['recent_rows_per_second']:.2f} rows/s "
        f"eta={_duration(report['generation_eta_seconds'])} "
        f"scores={report['score_slices']}/{report['expected_score_slices']}"
    )
    for record in report["records"]:
        print(
            "[final31-status:slice] "
            f"seed={record['seed']} model={record['model_slug']} "
            f"rows={record['durable_rows']}/{record['expected_rows']} "
            f"generated={record['generation_benchmarks']}/{record['expected_benchmarks']} "
            f"scored={record['score_slices']}/{record['expected_score_slices']}"
        )
    archive = report["archive"]
    print(
        "[final31-status:archive] "
        f"descriptors={archive['descriptors']} built={archive['built']} "
        f"uploaded={archive['uploaded']} failed={archive['failed']}"
    )
    if report["gpus"]:
        print(
            "[final31-status:gpus] "
            + " ".join(
                f"gpu{item['index']}={item['utilization']}%/{item['memory_used_mib']}MiB"
                for item in report["gpus"]
            )
        )
    for warning in report["warnings"]:
        print(f"[final31-status:warning] {warning}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign-root", type=Path, required=True)
    parser.add_argument("--score-root", type=Path)
    parser.add_argument("--dataset-manifest", type=Path, required=True)
    parser.add_argument("--archive-spool-root", type=Path)
    parser.add_argument("--model-slug", action="append", dest="model_slugs")
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 43, 44])
    parser.add_argument("--rate-window-seconds", type=float, default=300.0)
    parser.add_argument("--low-gpu-threshold", type=int, default=10)
    parser.add_argument("--gpu", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--watch", type=float, metavar="SECONDS")
    parser.add_argument("--fail-if-incomplete", action="store_true")
    args = parser.parse_args()
    args.campaign_root = args.campaign_root.expanduser().resolve()
    args.score_root = (
        args.score_root.expanduser().resolve()
        if args.score_root
        else args.campaign_root / "scoring"
    )
    args.archive_spool_root = (
        args.archive_spool_root.expanduser().resolve()
        if args.archive_spool_root
        else args.campaign_root / "hf_archive"
    )
    args.model_slugs = tuple(args.model_slugs or DEFAULT_MODELS)
    while True:
        report = collect_status(args)
        if args.json:
            print(json.dumps(report, indent=2, sort_keys=True))
        else:
            print_status(report)
        if not args.watch or report["complete"]:
            raise SystemExit(1 if args.fail_if_incomplete and not report["complete"] else 0)
        time.sleep(max(1.0, args.watch))


if __name__ == "__main__":
    main()
