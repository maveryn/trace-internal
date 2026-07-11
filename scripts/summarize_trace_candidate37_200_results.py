#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
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
    score_to_percent,
    score_path,
)


MODEL_COLUMNS = [
    ("qwen25vl3b-base", "Base"),
    ("trace-qwen25vl3b-easyr1-answer-nokl-step400", "Step 400"),
    ("trace-qwen25vl3b-easyr1-answer-nokl-step500", "Step 500"),
    ("trace-qwen25vl3b-easyr1-answer-nokl-step600", "Step 600"),
]
MODEL_LABELS = dict(MODEL_COLUMNS)


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _score_from_artifacts(path: Path, obj: dict[str, Any], rows: int | None) -> tuple[float | None, int | None]:
    artifacts = obj.get("artifacts", {})
    if not isinstance(artifacts, dict):
        return None, rows
    prediction_table = artifacts.get("prediction_table")
    if not prediction_table:
        return None, rows
    pred_path = Path(str(prediction_table))
    if not pred_path.is_absolute():
        pred_path = REPO_ROOT / pred_path

    # MM-HELIX writes category-level scores next to the prediction table but
    # returns None from the upstream evaluate() call. Use the weighted mean over
    # category item counts so the sampled suite has one comparable score.
    mmhelix_tsv = pred_path.with_name(f"{pred_path.stem}_results.tsv")
    if mmhelix_tsv.exists():
        table = pd.read_csv(mmhelix_tsv, sep="\t")
        if {"items", "average_score"}.issubset(table.columns):
            counts = pd.to_numeric(table["items"], errors="coerce").fillna(0.0)
            scores = pd.to_numeric(table["average_score"], errors="coerce").fillna(0.0)
            total = float(counts.sum())
            if total:
                return float((counts * scores).sum() / total * 100.0), int(total)

    return None, rows


def _score(path: Path) -> tuple[float | None, int | None]:
    obj = _load_json(path)
    if obj is None:
        return None, None
    score, rows = extract_score_and_rows(obj)
    if score is not None:
        return score, rows

    scores = obj.get("scores", {})
    if isinstance(scores, dict):
        table = scores.get("table")
        if isinstance(table, list):
            values: list[float] = []
            for row in table:
                if not isinstance(row, dict):
                    continue
                raw_values = row.get("average_scores")
                if isinstance(raw_values, str):
                    try:
                        raw_values = ast.literal_eval(raw_values)
                    except Exception:
                        raw_values = None
                if isinstance(raw_values, list):
                    for value in raw_values:
                        parsed = score_to_percent(value)
                        if parsed is not None:
                            values.append(parsed)
            if values:
                return sum(values) / len(values), rows

    return _score_from_artifacts(path, obj, rows)


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


def build_tables(
    benchmark_root: Path,
    run_root: Path,
    model_columns: list[tuple[str, str]],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
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
        for slug, label in model_columns:
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
        for _, model_label in model_columns:
            values = pd.to_numeric(summary.loc[mask, model_label], errors="coerce")
            avg[model_label] = values.mean(skipna=True)
            avg[f"{model_label} rows"] = ""
        summary = pd.concat([summary, pd.DataFrame([avg])], ignore_index=True)

    details = pd.DataFrame(detail_rows)
    generation = pd.DataFrame(gen_rows)
    return summary, details, generation


def _rows_label(row: pd.Series, model_columns: list[tuple[str, str]]) -> str:
    values = []
    for _, label in model_columns:
        value = row.get(f"{label} rows")
        if value not in ("", None) and not pd.isna(value):
            values.append(int(value))
    if not values:
        return ""
    if len(set(values)) == 1:
        return str(values[0])
    return "/".join(str(x) for x in values)


def write_markdown(summary: pd.DataFrame, output: Path, model_columns: list[tuple[str, str]]) -> None:
    first_label = model_columns[0][1] if model_columns else ""
    delta_labels = [label for _, label in model_columns[1:]] if first_label else []
    headers = ["Benchmark", "Prompt / Dataset", "Rows", *[label for _, label in model_columns]]
    headers.extend(f"{label} - {first_label}" for label in delta_labels)
    align = ["---", "---", "---:"] + ["---:"] * len(model_columns)
    align.extend(["---:"] * len(delta_labels))
    lines = [
        "# Qwen2.5-VL-3B TRACE Candidate37 200-Row Benchmark Results",
        "",
        f"Subset manifest root: `{TRACE_CANDIDATE37_200_SUBSET_ROOT.relative_to(REPO_ROOT)}`",
        "",
        "Each benchmark has exactly one normalized score. Scores are percentages when the evaluator reports accuracy-like metrics.",
        "",
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(align) + " |",
    ]
    for _, row in summary.iterrows():
        prompt = str(row.get("prompt_run") or row.get("dataset_alias") or "")
        if row["benchmark_key"].startswith("average"):
            prompt = ""
        cells = [str(row["benchmark"]), f"`{prompt}`" if prompt else "", _rows_label(row, model_columns)]
        for _, label in model_columns:
            cells.append(_fmt(row[label]))
        for label in delta_labels:
            try:
                cells.append(_fmt(float(row[label]) - float(row[first_label])))
            except Exception:
                cells.append("")
        lines.append("| " + " | ".join(cells) + " |")
    lines.extend(
        [
            "",
            "Normalization notes:",
            "- `MM-HELIX`: weighted mean over category `items * average_score` from the generated results TSV.",
            "- `TableVQABench`: macro mean over the reported split `average_scores` values.",
            "- `SEEPhys`: nested `Overall / Accuracy (%)` value.",
            "- Judge-backed datasets use the local Qwen3-32B judge configured by the queue.",
            "",
        ]
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")


def write_excel(
    summary: pd.DataFrame,
    details: pd.DataFrame,
    generation: pd.DataFrame,
    output: Path,
    model_columns: list[tuple[str, str]],
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    metadata = pd.DataFrame(
        [
            {"key": "suite", "value": "trace_candidate37_200"},
            {"key": "subset_root", "value": str(TRACE_CANDIDATE37_200_SUBSET_ROOT)},
            {"key": "benchmark_count", "value": len(benchmark_specs_for_run_set("trace_candidate37_200"))},
            {"key": "models", "value": ", ".join(slug for slug, _ in model_columns)},
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
    parser.add_argument("--models", nargs="*", default=[slug for slug, _ in MODEL_COLUMNS])
    parser.add_argument("--markdown", type=Path, default=REPO_ROOT / "results/qwen25vl3b_trace_candidate37_200_results.md")
    parser.add_argument("--excel", type=Path, default=REPO_ROOT / "results/qwen25vl3b_trace_candidate37_200_results.xlsx")
    parser.add_argument("--no-excel", action="store_true")
    args = parser.parse_args()
    model_columns = [(slug, MODEL_LABELS.get(slug, slug)) for slug in args.models]
    summary, details, generation = build_tables(args.benchmark_root, args.run_root, model_columns)
    write_markdown(summary, args.markdown, model_columns)
    if not args.no_excel:
        write_excel(summary, details, generation, args.excel, model_columns)
    print(f"[wrote] {args.markdown}")
    if not args.no_excel:
        print(f"[wrote] {args.excel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
