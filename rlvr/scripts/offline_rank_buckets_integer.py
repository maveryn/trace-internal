#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable


@dataclass
class BucketAgg:
    bucket_id_str: str
    task_variant_id: int
    task_variant_key: str
    count_bin: int
    n: int = 0
    correct: int = 0
    parse_ok: int = 0
    abs_error_sum: float = 0.0
    abs_error_n: int = 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Aggregate Prism integer eval predictions into per-bucket accuracy stats "
            "and a hard-to-easy bucket ranking order."
        )
    )
    parser.add_argument(
        "--predictions-jsonl",
        type=str,
        required=True,
        help="Path to merged predictions JSONL (e.g., predictions_all.jsonl).",
    )
    parser.add_argument(
        "--out-dir",
        type=str,
        default="",
        help="Output directory for bucket_stats.json and bucket_order.json (defaults to predictions parent).",
    )
    parser.add_argument(
        "--expected-bins",
        type=int,
        default=60,
        help="Expected number of unique bucket_id_str entries (default: 60).",
    )
    parser.add_argument(
        "--allow-uneven-bin-sizes",
        action="store_true",
        help="Allow bins to have different sample counts (default: strict equal-size check).",
    )
    parser.add_argument(
        "--expected-count-bins",
        type=int,
        default=4,
        help="Expected number of unique count_bin values (default: 4).",
    )
    parser.add_argument(
        "--print-top-k",
        type=int,
        default=10,
        help="How many hardest/easiest bins to print (default: 10).",
    )
    return parser.parse_args()


def _to_int(value: Any, default: int | None = None) -> int | None:
    if value is None:
        return default
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float) and value.is_integer():
        return int(value)
    try:
        return int(str(value).strip())
    except Exception:
        return default


def _to_float(value: Any, default: float | None = None) -> float | None:
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip())
    except Exception:
        return default


def _iter_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as fp:
        for lineno, line in enumerate(fp, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON at line {lineno} in {path}: {exc}") from exc


def _bucket_sort_key(item: Dict[str, Any]) -> tuple[int, int, str]:
    return (int(item.get("task_variant_id", -1)), int(item.get("count_bin", -1)), str(item.get("bucket_id_str", "")))


def _rank_sort_key(item: Dict[str, Any]) -> tuple[float, float, int, int, int, str]:
    return (
        -float(item.get("accuracy", 0.0)),
        -float(item.get("parse_rate", 0.0)),
        -int(item.get("n", 0)),
        int(item.get("task_variant_id", -1)),
        int(item.get("count_bin", -1)),
        str(item.get("bucket_id_str", "")),
    )


def main() -> int:
    args = _parse_args()

    predictions_path = Path(args.predictions_jsonl).expanduser().resolve()
    if not predictions_path.exists():
        raise FileNotFoundError(f"Predictions file not found: {predictions_path}")

    out_dir = Path(args.out_dir).expanduser().resolve() if args.out_dir else predictions_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    bucket_stats_path = out_dir / "bucket_stats.json"
    bucket_order_path = out_dir / "bucket_order.json"
    summary_path = out_dir / "bucket_rank_summary.json"

    by_bucket: dict[str, BucketAgg] = {}
    total_rows = 0

    for row in _iter_jsonl(predictions_path):
        total_rows += 1

        bucket_id_str = str(row.get("bucket_id_str", "") or "")
        if not bucket_id_str:
            raise ValueError("Missing `bucket_id_str` in predictions row.")

        task_variant_id = _to_int(row.get("task_variant_id"), default=-1)
        count_bin = _to_int(row.get("count_bin"), default=-1)
        task_variant_key = str(row.get("task_variant_key", "") or "")

        if bucket_id_str not in by_bucket:
            by_bucket[bucket_id_str] = BucketAgg(
                bucket_id_str=bucket_id_str,
                task_variant_id=int(task_variant_id if task_variant_id is not None else -1),
                task_variant_key=task_variant_key,
                count_bin=int(count_bin if count_bin is not None else -1),
            )

        agg = by_bucket[bucket_id_str]
        agg.n += 1
        agg.correct += int(bool(_to_int(row.get("correct"), default=0)))
        agg.parse_ok += int(bool(_to_int(row.get("parse_ok"), default=0)))

        abs_error = _to_float(row.get("abs_error"), default=None)
        if abs_error is not None:
            agg.abs_error_sum += float(abs_error)
            agg.abs_error_n += 1

    if total_rows == 0:
        raise ValueError(f"No prediction rows found in {predictions_path}")

    if len(by_bucket) != int(args.expected_bins):
        raise ValueError(
            f"Expected {args.expected_bins} buckets, found {len(by_bucket)}. "
            "Check probe coverage and prediction file."
        )

    bucket_stats: list[dict[str, Any]] = []
    for agg in by_bucket.values():
        n = int(agg.n)
        bucket_stats.append(
            {
                "bucket_id_str": agg.bucket_id_str,
                "task_variant_id": int(agg.task_variant_id),
                "task_variant_key": str(agg.task_variant_key),
                "count_bin": int(agg.count_bin),
                "n": n,
                "accuracy": (float(agg.correct) / n) if n else 0.0,
                "parse_rate": (float(agg.parse_ok) / n) if n else 0.0,
                "mae": (float(agg.abs_error_sum) / float(agg.abs_error_n)) if agg.abs_error_n else None,
            }
        )

    bucket_stats.sort(key=_bucket_sort_key)

    sample_counts = sorted({int(item["n"]) for item in bucket_stats})
    equal_bin_sizes = len(sample_counts) == 1
    if not args.allow_uneven_bin_sizes and not equal_bin_sizes:
        raise ValueError(
            "Bins are uneven. Sample counts observed: "
            f"{sample_counts}. Rerun probe/eval to get balanced coverage."
        )

    variant_ids = {int(item["task_variant_id"]) for item in bucket_stats}
    count_bins = {int(item["count_bin"]) for item in bucket_stats}
    if len(count_bins) != int(args.expected_count_bins):
        raise ValueError(
            f"Expected {args.expected_count_bins} count bins, found {len(count_bins)}: {sorted(count_bins)}"
        )

    rank_sorted = sorted(bucket_stats, key=_rank_sort_key)
    bucket_order = [str(item["bucket_id_str"]) for item in rank_sorted]

    # K_min: smallest hard-prefix that covers all variants and all count bins.
    seen_variants: set[int] = set()
    seen_count_bins: set[int] = set()
    k_min = len(bucket_order)
    for idx, item in enumerate(rank_sorted, start=1):
        seen_variants.add(int(item["task_variant_id"]))
        seen_count_bins.add(int(item["count_bin"]))
        if len(seen_variants) == len(variant_ids) and len(seen_count_bins) == len(count_bins):
            k_min = idx
            break

    summary = {
        "predictions_jsonl": str(predictions_path),
        "total_rows": int(total_rows),
        "bucket_count": int(len(bucket_stats)),
        "variant_count": int(len(variant_ids)),
        "count_bins": sorted(int(v) for v in count_bins),
        "n_per_bucket_values": sample_counts,
        "equal_bin_sizes": bool(equal_bin_sizes),
        "k_min": int(k_min),
        "ranking_policy": {
            "easy_to_hard": "accuracy desc, parse_rate desc, n desc, task_variant_id asc, count_bin asc",
            "iou_or_reward_used": "integer correctness from predictions JSONL",
        },
        "outputs": {
            "bucket_stats_json": str(bucket_stats_path),
            "bucket_order_json": str(bucket_order_path),
            "summary_json": str(summary_path),
        },
    }

    bucket_stats_path.write_text(json.dumps(bucket_stats, indent=2), encoding="utf-8")
    bucket_order_path.write_text(json.dumps(bucket_order, indent=2), encoding="utf-8")
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    top_k = max(1, int(args.print_top_k))
    easiest = rank_sorted[:top_k]
    hardest = rank_sorted[-top_k:]

    print(f"[done] rows={total_rows} buckets={len(bucket_stats)} variants={len(variant_ids)}")
    print(f"[done] equal_bin_sizes={equal_bin_sizes} n_values={sample_counts}")
    print(f"[done] k_min={k_min}")
    print(f"[done] wrote: {bucket_stats_path}")
    print(f"[done] wrote: {bucket_order_path}")
    print(f"[done] wrote: {summary_path}")

    print("[easiest]")
    for item in easiest:
        print(
            f"  {item['bucket_id_str']}: acc={item['accuracy']:.4f} "
            f"parse={item['parse_rate']:.4f} n={item['n']}"
        )

    print("[hardest]")
    for item in hardest:
        print(
            f"  {item['bucket_id_str']}: acc={item['accuracy']:.4f} "
            f"parse={item['parse_rate']:.4f} n={item['n']}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
