#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from benchmark_queue_lib import (
    DEFAULT_BENCHMARK_ROOT,
    DEFAULT_RUN_ROOT,
    REPO_ROOT,
    TRACE_CANDIDATE37_200_SUBSET_ROOT,
    benchmark_specs_for_run_set,
    extract_score_and_rows,
    run_dir,
    score_path,
)


MODEL_COLUMNS = [
    ("qwen25vl3b-base", "Base"),
    ("trace-qwen25vl3b-easyr1-answer-nokl-step400", "Step 400"),
    ("trace-qwen25vl3b-easyr1-answer-nokl-step500", "Step 500"),
    ("trace-qwen25vl3b-easyr1-answer-nokl-step600", "Step 600"),
]


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _score(path: Path) -> tuple[float | None, int | None]:
    obj = _load_json(path)
    if obj is None:
        return None, None
    return extract_score_and_rows(obj)


def _generation_stats(path: Path) -> dict[str, Any]:
    obj = _load_json(path)
    if not obj:
        return {}
    stats = obj.get("output_token_stats") or {}
    return {
        "response_mean": stats.get("mean"),
        "response_max": stats.get("max"),
        "length_cap_fraction": stats.get("length_cap_fraction"),
        "generation_rows": obj.get("rows"),
        "generation_elapsed_sec": obj.get("generation_elapsed_sec"),
    }


def _fmt(value: Any) -> str:
    if value is None:
        return ""
    try:
        return f"{float(value):.2f}"
    except Exception:
        return str(value)


def build_tables(benchmark_root: Path, run_root: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    specs = benchmark_specs_for_run_set("trace_candidate37_200")
    summary_rows: list[dict[str, Any]] = []
    detail_rows: list[dict[str, Any]] = []
    gen_rows: list[dict[str, Any]] = []

    for spec in specs:
        row = {
            "benchmark_key": spec.key,
            "benchmark": spec.display,
            "dataset_alias": spec.alias,
            "prompt_run": spec.run_name,
        }
        for slug, label in MODEL_COLUMNS:
            spath = score_path(spec, slug, benchmark_root)
            score, n_rows = _score(spath)
            row[label] = score
            row[f"{label} rows"] = n_rows
            detail_rows.append(
                {
                    "model_slug": slug,
                    "model": label,
                    "benchmark_key": spec.key,
                    "benchmark": spec.display,
                    "dataset_alias": spec.alias,
                    "prompt_run": spec.run_name,
                    "score": score,
                    "rows": n_rows,
                    "score_path": str(spath) if spath.exists() else "",
                }
            )
            gpath = run_dir(spec, slug, run_root) / "generation_summary.json"
            stats = _generation_stats(gpath)
            if stats:
                gen_rows.append(
                    {
                        "model_slug": slug,
                        "model": label,
                        "benchmark_key": spec.key,
                        "benchmark": spec.display,
                        "dataset_alias": spec.alias,
                        "prompt_run": spec.run_name,
                        "generation_summary": str(gpath),
                        **stats,
                    }
                )
        summary_rows.append(row)

    summary = pd.DataFrame(summary_rows)
    for exclude_screenspot in (False, True):
        label = "Average excl. ScreenSpot" if exclude_screenspot else "Average"
        mask = pd.Series([True] * len(summary))
        if exclude_screenspot:
            mask = ~summary["benchmark_key"].str.contains("screenspot", case=False, na=False)
        avg: dict[str, Any] = {
            "benchmark_key": "average_excluding_screenspot" if exclude_screenspot else "average",
            "benchmark": label,
            "dataset_alias": "",
            "prompt_run": "",
        }
        for _, model_label in MODEL_COLUMNS:
            values = pd.to_numeric(summary.loc[mask, model_label], errors="coerce")
            avg[model_label] = values.mean(skipna=True)
            avg[f"{model_label} rows"] = ""
        summary = pd.concat([summary, pd.DataFrame([avg])], ignore_index=True)

    details = pd.DataFrame(detail_rows)
    generation = pd.DataFrame(gen_rows)
    return summary, details, generation


def write_markdown(summary: pd.DataFrame, output: Path) -> None:
    lines = [
        "# Qwen2.5-VL-3B TRACE Candidate37 200-Row Benchmark Results",
        "",
        f"Subset manifest root: `{TRACE_CANDIDATE37_200_SUBSET_ROOT.relative_to(REPO_ROOT)}`",
        "",
        "| Benchmark | Prompt / Dataset | Base | Step 400 | Step 500 | Step 600 |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for _, row in summary.iterrows():
        prompt = str(row.get("prompt_run") or row.get("dataset_alias") or "")
        if row["benchmark_key"].startswith("average"):
            prompt = ""
        lines.append(
            f"| {row['benchmark']} | `{prompt}` | "
            f"{_fmt(row['Base'])} | {_fmt(row['Step 400'])} | {_fmt(row['Step 500'])} | {_fmt(row['Step 600'])} |"
        )
    lines.extend(
        [
            "",
            "Scores are percentages when the evaluator reports accuracy-like metrics. "
            "Judge-backed datasets use the local Qwen3-32B judge configured by the queue.",
            "",
        ]
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")


def write_excel(summary: pd.DataFrame, details: pd.DataFrame, generation: pd.DataFrame, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    metadata = pd.DataFrame(
        [
            {"key": "suite", "value": "trace_candidate37_200"},
            {"key": "subset_root", "value": str(TRACE_CANDIDATE37_200_SUBSET_ROOT)},
            {"key": "benchmark_count", "value": len(benchmark_specs_for_run_set("trace_candidate37_200"))},
            {"key": "models", "value": ", ".join(slug for slug, _ in MODEL_COLUMNS)},
        ]
    )
    with pd.ExcelWriter(output) as writer:
        summary.to_excel(writer, sheet_name="summary", index=False)
        details.to_excel(writer, sheet_name="details", index=False)
        generation.to_excel(writer, sheet_name="generation_stats", index=False)
        metadata.to_excel(writer, sheet_name="metadata", index=False)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark-root", type=Path, default=DEFAULT_BENCHMARK_ROOT)
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT)
    parser.add_argument("--markdown", type=Path, default=REPO_ROOT / "results/qwen25vl3b_trace_candidate37_200_results.md")
    parser.add_argument("--excel", type=Path, default=REPO_ROOT / "results/qwen25vl3b_trace_candidate37_200_results.xlsx")
    args = parser.parse_args()
    summary, details, generation = build_tables(args.benchmark_root, args.run_root)
    write_markdown(summary, args.markdown)
    write_excel(summary, details, generation, args.excel)
    print(f"[wrote] {args.markdown}")
    print(f"[wrote] {args.excel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
