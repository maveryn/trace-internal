#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd

from benchmark_queue_lib import REPO_ROOT, TRACE_GROUNDING_BENCHMARKS, TRACE_GROUNDING_SUBSET_ROOT
from summarize_trace_candidate37_200_results import build_tables


MODEL_COLUMNS = [
    ("qwen25vl3b-base", "Base"),
    ("trace-qwen25vl3b-easyr1-all1000-answer-nokl-step500", "Answer GRPO 500"),
    ("trace-qwen25vl3b-rlvr-ann-additive-0p50-sectioned-step500", "Annotation GRPO 500"),
]


def _add_deltas(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    for column in ("Base", "Answer GRPO 500", "Annotation GRPO 500"):
        out[column] = pd.to_numeric(out[column], errors="coerce")
    out["Answer - Base"] = out["Answer GRPO 500"] - out["Base"]
    out["Annotation - Base"] = out["Annotation GRPO 500"] - out["Base"]
    out["Annotation - Answer"] = out["Annotation GRPO 500"] - out["Answer GRPO 500"]
    return out


def _fmt(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
        return f"{float(value):.2f}"
    except Exception:
        return str(value)


def _rows_label(row: pd.Series) -> str:
    values = []
    for label in ("Base", "Answer GRPO 500", "Annotation GRPO 500"):
        value = row.get(f"{label} rows")
        if value not in ("", None) and not pd.isna(value):
            values.append(int(value))
    if not values:
        return ""
    if len(set(values)) == 1:
        return str(values[0])
    return "/".join(str(value) for value in values)


def _markdown_table(frame: pd.DataFrame, title: str) -> list[str]:
    headers = [
        "Benchmark",
        "Rows",
        "Base",
        "Answer GRPO 500",
        "Annotation GRPO 500",
        "Answer - Base",
        "Annotation - Base",
        "Annotation - Answer",
    ]
    lines = [
        f"## {title}",
        "",
        "| " + " | ".join(headers) + " |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for _, row in frame.iterrows():
        cells = [
            str(row["benchmark"]),
            _rows_label(row),
            _fmt(row["Base"]),
            _fmt(row["Answer GRPO 500"]),
            _fmt(row["Annotation GRPO 500"]),
            _fmt(row["Answer - Base"]),
            _fmt(row["Annotation - Base"]),
            _fmt(row["Annotation - Answer"]),
        ]
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")
    return lines


def _score_sheet(
    *,
    benchmark_root: Path,
    run_root: Path,
    only: list[str],
    run_set: str,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    summary, details, generation = build_tables(
        benchmark_root=benchmark_root,
        run_root=run_root,
        model_columns=MODEL_COLUMNS,
        run_set=run_set,
        only=only,
        exclude=[],
    )
    summary = summary[summary["benchmark_key"] != "average_excluding_screenspot"].reset_index(drop=True)
    return _add_deltas(summary), details, generation


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--greedy-benchmark-root", type=Path, required=True)
    parser.add_argument("--greedy-run-root", type=Path, required=True)
    parser.add_argument("--temp06-benchmark-root", type=Path, required=True)
    parser.add_argument("--temp06-run-root", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, default=REPO_ROOT / "results/trace_grounding_qwen25vl3b_base_answer_annotation_greedy_temp06.md")
    parser.add_argument("--excel", type=Path, default=REPO_ROOT / "results/trace_grounding_qwen25vl3b_base_answer_annotation_greedy_temp06.xlsx")
    parser.add_argument("--subset-root", type=Path, default=TRACE_GROUNDING_SUBSET_ROOT)
    parser.add_argument("--only", nargs="*", default=list(TRACE_GROUNDING_BENCHMARKS))
    parser.add_argument("--run-set", default="trace_grounding")
    parser.add_argument("--title", default="TRACE Grounding 3B Base / Answer / Annotation Results")
    args = parser.parse_args()

    greedy, greedy_details, greedy_generation = _score_sheet(
        benchmark_root=args.greedy_benchmark_root,
        run_root=args.greedy_run_root,
        only=args.only,
        run_set=args.run_set,
    )
    temp06, temp06_details, temp06_generation = _score_sheet(
        benchmark_root=args.temp06_benchmark_root,
        run_root=args.temp06_run_root,
        only=args.only,
        run_set=args.run_set,
    )

    lines = [
        f"# {args.title}",
        "",
        f"Subset manifest root: `{args.subset_root}`",
        "",
        "Scores are canonical VLMEvalKit grounding metrics normalized to percentages.",
        "",
    ]
    lines.extend(_markdown_table(greedy, "Greedy, max_tokens=4096"))
    lines.extend(_markdown_table(temp06, "Temperature 0.6, max_tokens=4096"))
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.write_text("\n".join(lines), encoding="utf-8")

    metadata = pd.DataFrame(
        [
            {"key": "suite", "value": "trace_grounding_qwen25vl3b_base_answer_annotation"},
            {"key": "subset_root", "value": str(args.subset_root)},
            {"key": "benchmarks", "value": ", ".join(args.only)},
            {"key": "run_set", "value": args.run_set},
            {"key": "models", "value": ", ".join(slug for slug, _ in MODEL_COLUMNS)},
            {"key": "greedy_run_root", "value": str(args.greedy_run_root)},
            {"key": "greedy_benchmark_root", "value": str(args.greedy_benchmark_root)},
            {"key": "temp06_run_root", "value": str(args.temp06_run_root)},
            {"key": "temp06_benchmark_root", "value": str(args.temp06_benchmark_root)},
        ]
    )
    args.excel.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(args.excel) as writer:
        greedy.to_excel(writer, sheet_name="greedy", index=False)
        temp06.to_excel(writer, sheet_name="temp0.6", index=False)
        greedy_details.to_excel(writer, sheet_name="details_greedy", index=False)
        temp06_details.to_excel(writer, sheet_name="details_temp0.6", index=False)
        greedy_generation.to_excel(writer, sheet_name="generation_greedy", index=False)
        temp06_generation.to_excel(writer, sheet_name="generation_temp0.6", index=False)
        metadata.to_excel(writer, sheet_name="metadata", index=False)

    print(f"[wrote] {args.markdown}")
    print(f"[wrote] {args.excel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
