#!/usr/bin/env python3
"""Export calibration stats/workbooks from a TRACE curriculum probe run."""

from __future__ import annotations

import argparse
import gzip
import io
import json
import re
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

import pandas as pd
import zstandard as zstd

from trace.core.taxonomy import resolve_task_taxonomy


def _json_loads(value: Any) -> Any:
    if isinstance(value, str):
        return json.loads(value)
    return value


def _scalar(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return json.dumps(value, sort_keys=True)


def _safe_sheet_name(name: str) -> str:
    return name[:31]


def _load_trace_records(dataset_root: Path) -> dict[str, dict[str, Any]]:
    trace_dir = dataset_root / "traces"
    records: dict[str, dict[str, Any]] = {}
    for shard in sorted(trace_dir.glob("*.jsonl.zst")):
        with shard.open("rb") as fh:
            reader = zstd.ZstdDecompressor().stream_reader(fh)
            text_reader = io.TextIOWrapper(reader, encoding="utf-8")
            for line in text_reader:
                if not line.strip():
                    continue
                record = json.loads(line)
                records[str(record["instance_id"])] = record
    return records


def _instance_trace_fields(record: dict[str, Any]) -> dict[str, Any]:
    execution = record.get("execution_trace") or {}
    query = record.get("query_spec") or {}
    params = query.get("params") or {}
    render = record.get("render_spec") or {}
    answer = _json_loads(record.get("answer_gt") or {})

    row_count = execution.get("row_count")
    numeric_column_count = execution.get("numeric_column_count")
    fields: dict[str, Any] = {
        "query_id": execution.get("query_id") or query.get("query_id") or params.get("query_id"),
        "question_format": execution.get("question_format") or params.get("question_format"),
        "scene_variant": execution.get("scene_variant") or render.get("scene_variant"),
        "row_count": row_count,
        "visible_row_count": row_count + 1 if isinstance(row_count, int) else None,
        "numeric_column_count": numeric_column_count,
        "total_column_count": numeric_column_count + 1 if isinstance(numeric_column_count, int) else None,
        "answer": _scalar(answer.get("value") if isinstance(answer, dict) else answer),
    }

    for source in (params, execution):
        for key, value in source.items():
            if key in fields or key.endswith("_probabilities"):
                continue
            if isinstance(value, (str, int, float, bool)) or value is None:
                fields[key] = value
    return fields


def _summarize(rows: list[dict[str, Any]], *, hard_threshold: int, easy_threshold: int) -> dict[str, Any]:
    prompt_count = len(rows)
    rollout_count = sum(int(row.get("rollout_count") or 0) for row in rows)
    positive_count = sum(int(row.get("solved_rollouts") or 0) for row in rows)
    solved = [int(row.get("solved_rollouts") or 0) for row in rows]
    hard_count = sum(1 for value in solved if value <= hard_threshold)
    easy_count = sum(1 for value in solved if value >= easy_threshold)
    band_count = sum(1 for value in solved if hard_threshold < value < easy_threshold)
    return {
        "name": "overall",
        "prompt_count": prompt_count,
        "rollout_count": rollout_count,
        "positive_rollout_count": positive_count,
        "mean_solve_rate": float(positive_count / rollout_count) if rollout_count else 0.0,
        "hard_count": hard_count,
        "hard_frac": float(hard_count / prompt_count) if prompt_count else 0.0,
        "easy_count": easy_count,
        "easy_frac": float(easy_count / prompt_count) if prompt_count else 0.0,
        "band_count": band_count,
        "band_frac": float(band_count / prompt_count) if prompt_count else 0.0,
        "min_solved_rollouts": min(solved) if solved else 0,
        "median_solved_rollouts": float(statistics.median(solved)) if solved else 0.0,
        "max_solved_rollouts": max(solved) if solved else 0,
    }


def _group_summaries(rows: list[dict[str, Any]], key: str, *, hard_threshold: int, easy_threshold: int) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        value = row.get(key)
        if value is None:
            continue
        grouped[str(value)].append(row)
    summaries: dict[str, dict[str, Any]] = {}
    for name, group_rows in sorted(grouped.items(), key=lambda item: item[0]):
        summary = _summarize(group_rows, hard_threshold=hard_threshold, easy_threshold=easy_threshold)
        summary["name"] = name
        summaries[name] = summary
    return summaries


def _read_per_instance(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open() as fh:
        for line in fh:
            if not line.strip():
                continue
            record = json.loads(line)
            solved = int(record.get("positive_rollout_count") or 0)
            record["solved_rollouts"] = solved
            rows.append(record)
    return rows


def _read_per_rollout_tokens(path: Path) -> list[int]:
    if not path.exists():
        return []
    opener = gzip.open if str(path).endswith(".gz") else open
    tokens: list[int] = []
    with opener(path, "rt", encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            if not line.strip():
                continue
            record = json.loads(line)
            if "generated_tokens" in record:
                tokens.append(int(record.get("generated_tokens") or 0))
    return tokens


def _percentile(sorted_values: list[int], percentile: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    rank = (len(sorted_values) - 1) * float(percentile)
    lower = int(rank)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = rank - lower
    return float((sorted_values[lower] * (1.0 - weight)) + (sorted_values[upper] * weight))


def _token_stats(values: list[int], *, limit: int | None = None, cap_value: int | None = None) -> dict[str, Any]:
    sorted_values = sorted(int(value) for value in values)
    count = len(sorted_values)
    payload: dict[str, Any] = {
        "count": count,
        "min": int(sorted_values[0]) if sorted_values else 0,
        "p50": _percentile(sorted_values, 0.50),
        "p90": _percentile(sorted_values, 0.90),
        "p95": _percentile(sorted_values, 0.95),
        "p99": _percentile(sorted_values, 0.99),
        "max": int(sorted_values[-1]) if sorted_values else 0,
    }
    if limit is not None:
        over_limit_count = sum(1 for value in sorted_values if int(value) > int(limit))
        payload["limit"] = int(limit)
        payload["over_limit_count"] = int(over_limit_count)
        payload["over_limit_rate"] = float(over_limit_count / count) if count else 0.0
    if cap_value is not None:
        cap_count = sum(1 for value in sorted_values if int(value) >= int(cap_value))
        payload["cap_value"] = int(cap_value)
        payload["cap_count"] = int(cap_count)
        payload["cap_rate"] = float(cap_count / count) if count else 0.0
    return payload


def _load_dataset_root(parquet: Path, dataset_root: str | None) -> Path:
    if dataset_root:
        return Path(dataset_root)
    manifest = parquet.with_suffix(parquet.suffix + ".manifest.json")
    data = json.loads(manifest.read_text())
    return Path(data["trace_dataset_root"])


def export_stats(
    *,
    task_id: str,
    parquet: Path,
    probe_output_dir: Path,
    dataset_root: Path,
    out_root: Path,
    review_label: str,
    calibration_baseline: str,
    hard_threshold: int,
    easy_threshold: int,
    max_prompt_length: int,
    max_response_length: int,
    extra_group_keys: list[str] | None = None,
) -> dict[str, Any]:
    probe_rows = _read_per_instance(probe_output_dir / "per_instance.jsonl")
    response_tokens = _read_per_rollout_tokens(probe_output_dir / "per_rollout.jsonl.gz")
    parquet_df = pd.read_parquet(parquet)
    parquet_by_uid = {str(row.uid): row for row in parquet_df.itertuples(index=False)}
    trace_records = _load_trace_records(dataset_root)

    rows: list[dict[str, Any]] = []
    for probe_row in probe_rows:
        uid = str(probe_row["uid"])
        parquet_row = parquet_by_uid[uid]
        trace_record = trace_records[str(parquet_row.instance_id)]
        trace_fields = _instance_trace_fields(trace_record)
        rollout_count = int(probe_row.get("rollout_count") or 0)
        solved = int(probe_row.get("positive_rollout_count") or 0)
        row = {
            "dataset_index": int(probe_row["dataset_index"]),
            "uid": uid,
            "instance_id": str(parquet_row.instance_id),
            "task": task_id,
            "complexity_score": float(probe_row.get("complexity_score") or 0.0),
            "difficulty_bin": int(probe_row.get("difficulty_bin") or 0),
            "prompt_length": int(probe_row.get("prompt_length") or 0),
            "rollout_count": rollout_count,
            "solved_rollouts": solved,
            "solve_rate": float(solved / rollout_count) if rollout_count else 0.0,
            "hard": solved <= hard_threshold,
            "easy": solved >= easy_threshold,
            "band": hard_threshold < solved < easy_threshold,
            "max_token_rollout_count": int(probe_row.get("max_token_rollout_count") or 0),
            "extraction_none_count": int(probe_row.get("extraction_none_count") or 0),
            "crop_or_no_extract_rollout_count": int(probe_row.get("crop_or_no_extract_rollout_count") or 0),
        }
        row.update(trace_fields)
        rows.append(row)

    group_keys = [
        "query_id",
        "question_format",
        "row_count",
        "numeric_column_count",
        "total_column_count",
        "scene_variant",
        "solved_rollouts",
        "answer",
    ]
    for key in extra_group_keys or []:
        if key not in group_keys:
            group_keys.append(key)
    stats: dict[str, Any] = {
        "config": {
            "calibration_baseline": str(calibration_baseline),
            "task_id": task_id,
            "parquet": str(parquet),
            "dataset_root": str(dataset_root),
            "probe_output_dir": str(probe_output_dir),
            "rollouts_per_prompt": max((int(row["rollout_count"]) for row in rows), default=0),
            "hard_threshold_solved_rollouts": hard_threshold,
            "easy_threshold_solved_rollouts": easy_threshold,
            "hard_definition": f"solved_rollouts <= {hard_threshold}",
            "easy_definition": f"solved_rollouts >= {easy_threshold}",
            "max_prompt_length": int(max_prompt_length),
            "max_response_length": int(max_response_length),
        },
        "overall": _summarize(rows, hard_threshold=hard_threshold, easy_threshold=easy_threshold),
        "prompt_token_stats": _token_stats(
            [int(row.get("prompt_length") or 0) for row in rows],
            limit=int(max_prompt_length),
        ),
        "response_token_stats": _token_stats(
            response_tokens,
            cap_value=int(max_response_length),
        ),
    }
    for key in group_keys:
        grouped = _group_summaries(rows, key, hard_threshold=hard_threshold, easy_threshold=easy_threshold)
        if grouped:
            stats[f"by_{key}"] = grouped

    stats_path = probe_output_dir / "calibration_stats.json"
    stats_path.write_text(json.dumps(stats, indent=2, sort_keys=True) + "\n")

    taxonomy = resolve_task_taxonomy(str(task_id))
    domain_match = re.match(r"^task_([a-z0-9]+)_", str(task_id))
    domain = str(taxonomy.domain or (domain_match.group(1) if domain_match else "unknown"))
    scene_id = str(taxonomy.scene_id or "unknown_scene")
    review_dir = out_root / domain / scene_id / task_id
    review_dir.mkdir(parents=True, exist_ok=True)
    workbook_path = review_dir / f"{task_id}_{review_label}_solve_rate_distribution.xlsx"
    with pd.ExcelWriter(workbook_path, engine="openpyxl") as writer:
        pd.DataFrame([stats["overall"]]).to_excel(writer, sheet_name="summary", index=False)
        pd.DataFrame([stats["prompt_token_stats"]]).to_excel(writer, sheet_name="prompt_tokens", index=False)
        pd.DataFrame([stats["response_token_stats"]]).to_excel(writer, sheet_name="response_tokens", index=False)
        for key in group_keys:
            grouped = stats.get(f"by_{key}")
            if not grouped:
                continue
            pd.DataFrame(grouped.values()).to_excel(writer, sheet_name=_safe_sheet_name(f"by_{key}"), index=False)
        instance_columns = [
            "dataset_index",
            "uid",
            "query_id",
            "question_format",
            "scene_variant",
            "row_count",
            "numeric_column_count",
            "total_column_count",
            "answer",
            "rollout_count",
            "solved_rollouts",
            "solve_rate",
            "hard",
            "easy",
            "band",
            "complexity_score",
            "difficulty_bin",
            "prompt_length",
            "max_token_rollout_count",
            "extraction_none_count",
            "crop_or_no_extract_rollout_count",
        ]
        row_df = pd.DataFrame(rows)
        for key in extra_group_keys or []:
            if key in row_df.columns and key not in instance_columns:
                instance_columns.append(key)
        pd.DataFrame(row_df)[instance_columns].to_excel(writer, sheet_name="per_instance", index=False)

    stats["artifacts"] = {
        "calibration_stats": str(stats_path),
        "solve_workbook": str(workbook_path),
    }
    stats_path.write_text(json.dumps(stats, indent=2, sort_keys=True) + "\n")
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--parquet", required=True, type=Path)
    parser.add_argument("--probe-output-dir", required=True, type=Path)
    parser.add_argument("--dataset-root")
    parser.add_argument("--out-root", default="plans/task-reviews", type=Path)
    parser.add_argument("--review-label", default="v0")
    parser.add_argument("--calibration-baseline", default="v0")
    parser.add_argument("--hard-threshold", default=4, type=int)
    parser.add_argument("--easy-threshold", default=24, type=int)
    parser.add_argument("--max-prompt-length", default=2048, type=int)
    parser.add_argument("--max-response-length", default=2048, type=int)
    parser.add_argument(
        "--group-key",
        action="append",
        default=[],
        help="Additional trace scalar key to include as a grouped workbook/stat sheet. Repeatable.",
    )
    args = parser.parse_args()

    dataset_root = _load_dataset_root(args.parquet, args.dataset_root)
    stats = export_stats(
        task_id=args.task_id,
        parquet=args.parquet,
        probe_output_dir=args.probe_output_dir,
        dataset_root=dataset_root,
        out_root=args.out_root,
        review_label=args.review_label,
        calibration_baseline=args.calibration_baseline,
        hard_threshold=args.hard_threshold,
        easy_threshold=args.easy_threshold,
        max_prompt_length=args.max_prompt_length,
        max_response_length=args.max_response_length,
        extra_group_keys=args.group_key,
    )
    overall = stats["overall"]
    print(
        f"{args.task_id}: hard={overall['hard_frac']:.3f} "
        f"easy={overall['easy_frac']:.3f} band={overall['band_frac']:.3f} "
        f"mean={overall['mean_solve_rate']:.3f}"
    )
    print(stats["artifacts"]["solve_workbook"])


if __name__ == "__main__":
    main()
