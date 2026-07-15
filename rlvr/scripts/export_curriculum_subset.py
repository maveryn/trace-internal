#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


DEFAULT_SOURCE_PARQUET = Path("rlvr/dataset/train/trace_rlvr_train_128k_all_tasks_verojson.parquet")
DEFAULT_PROBE_JSONL = Path("rlvr/outputs/curriculum_probe/base_qwen3vl_2b_32x_tp1/per_instance.jsonl")
DEFAULT_OUTPUT_PARQUET = Path("rlvr/dataset/train/trace_rlvr_train_55k_solve_0125_0875_uniform.parquet")

PROBE_COLUMNS = [
    "uid",
    "dataset_index",
    "rollout_count",
    "positive_rollout_count",
    "perfect_rollout_count",
    "solve_rate",
    "perfect_rate",
    "zero_solve",
    "perfect_solve",
    "mean_task_reward",
    "mean_answer_reward",
    "mean_overall_reward",
    "mean_format_reward",
    "json_found_rate",
    "format_json_ok_rate",
    "format_schema_ok_rate",
    "probe_extraction_fallback_rate",
    "mean_generated_tokens",
    "max_generated_tokens",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Filter a Trace RLVR training parquet using empirical per-instance solve rates from "
            "trace_curriculum_probe.py, then export a retained subset parquet for training."
        )
    )
    parser.add_argument(
        "--source-parquet",
        type=Path,
        default=DEFAULT_SOURCE_PARQUET,
        help="Original Trace RLVR train parquet.",
    )
    parser.add_argument(
        "--probe-jsonl",
        type=Path,
        default=DEFAULT_PROBE_JSONL,
        help="Per-instance JSONL emitted by trace_curriculum_probe.py.",
    )
    parser.add_argument(
        "--output-parquet",
        type=Path,
        default=DEFAULT_OUTPUT_PARQUET,
        help="Output parquet path for the retained subset.",
    )
    parser.add_argument(
        "--min-solve-rate",
        type=float,
        default=0.125,
        help="Inclusive lower solve-rate bound.",
    )
    parser.add_argument(
        "--max-solve-rate",
        type=float,
        default=0.875,
        help="Inclusive upper solve-rate bound.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.min_solve_rate > args.max_solve_rate:
        raise ValueError("--min-solve-rate must be <= --max-solve-rate")

    source_parquet = args.source_parquet.resolve()
    probe_jsonl = args.probe_jsonl.resolve()
    output_parquet = args.output_parquet.resolve()
    output_parquet.parent.mkdir(parents=True, exist_ok=True)

    source_df = pd.read_parquet(source_parquet)
    probe_df = pd.read_json(probe_jsonl, lines=True)

    if "uid" not in source_df.columns:
        raise KeyError(f"{source_parquet} does not contain 'uid'")
    if "uid" not in probe_df.columns or "solve_rate" not in probe_df.columns:
        raise KeyError(f"{probe_jsonl} must contain 'uid' and 'solve_rate'")
    if len(source_df) != len(probe_df):
        raise ValueError(
            f"Source/probe row mismatch: source={len(source_df)} probe={len(probe_df)}; "
            "the probe must correspond to the source parquet."
        )
    if not source_df["uid"].is_unique:
        raise ValueError("Source parquet uid column must be unique.")
    if not probe_df["uid"].is_unique:
        raise ValueError("Probe uid column must be unique.")

    keep_mask = probe_df["solve_rate"].between(args.min_solve_rate, args.max_solve_rate, inclusive="both")
    kept_probe_df = probe_df.loc[keep_mask, PROBE_COLUMNS].copy()

    retained_df = source_df.merge(kept_probe_df, on="uid", how="inner", validate="one_to_one")
    retained_df = retained_df.reset_index(drop=True)
    retained_df.to_parquet(output_parquet, index=False)

    summary = {
        "source_parquet": str(source_parquet),
        "probe_jsonl": str(probe_jsonl),
        "output_parquet": str(output_parquet),
        "source_prompt_count": int(len(source_df)),
        "retained_prompt_count": int(len(retained_df)),
        "retained_fraction": float(len(retained_df) / len(source_df)) if len(source_df) else 0.0,
        "min_solve_rate": float(args.min_solve_rate),
        "max_solve_rate": float(args.max_solve_rate),
        "retained_mean_solve_rate": float(retained_df["solve_rate"].mean()) if len(retained_df) else 0.0,
        "retained_min_solve_rate": float(retained_df["solve_rate"].min()) if len(retained_df) else 0.0,
        "retained_max_solve_rate": float(retained_df["solve_rate"].max()) if len(retained_df) else 0.0,
        "retained_tasks": int(retained_df["task"].nunique()) if "task" in retained_df.columns else None,
    }
    summary_path = output_parquet.with_suffix(".summary.json")
    with summary_path.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, sort_keys=True)

    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
