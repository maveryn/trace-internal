#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from benchmark_queue_lib import BENCHMARKS, DEFAULT_BENCHMARK_ROOT, REPO_ROOT, extract_score_and_rows


DISPLAY_BY_KEY = {spec.key: spec.display for spec in BENCHMARKS}
DISPLAY_BY_KEY["screenspotpro"] = "ScreenSpotPro"
MODEL_COLUMNS = [
    "qwen3-vl-4b-instruct",
    "trace-qwen3vl4b-alpha0-answer-step250",
    "trace-qwen3vl4b-alpha0-5-answer-step250",
    "trace-qwen3vl4b-alpha1-answer-step250",
]


def _score_rows(path: Path) -> tuple[float | None, int | None]:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None, None
    return extract_score_and_rows(obj)


def _iter_score_files(root: Path):
    for path in sorted(root.glob("*/*/*/scores.json")):
        parts = path.relative_to(root).parts
        if len(parts) != 4:
            continue
        key, model_slug, run_name, _ = parts
        yield key, model_slug, run_name, path


def build_markdown(root: Path) -> str:
    rows: list[dict[str, Any]] = []
    for key, model_slug, run_name, path in _iter_score_files(root):
        score, n_rows = _score_rows(path)
        rows.append(
            {
                "benchmark": DISPLAY_BY_KEY.get(key, key),
                "key": key,
                "model": model_slug,
                "run": run_name,
                "rows": n_rows,
                "score": score,
                "path": path,
            }
        )

    rows.sort(key=lambda r: (r["model"], r["benchmark"], r["run"]))
    benchmark_order = {DISPLAY_BY_KEY.get(spec.key, spec.key): i for i, spec in enumerate(BENCHMARKS)}
    benchmark_order["ScreenSpotPro"] = len(BENCHMARKS)
    comparison: dict[str, dict[str, float | None]] = {}
    for row in rows:
        if row["model"] not in MODEL_COLUMNS:
            continue
        comparison.setdefault(row["benchmark"], {})[row["model"]] = row["score"]

    lines = [
        "# External Benchmark Results",
        "",
        "Scores are collected from `benchmark/<dataset>/<model>/<run_name>/scores.json`.",
        "Generation setup follows the benchmark-specific policy in `benchmark/evaluation_plan.md`.",
        "",
        "## Model Comparison",
        "",
        "| Benchmark | `qwen3-vl-4b-instruct` | `trace-qwen3vl4b-alpha0-answer-step250` | `trace-qwen3vl4b-alpha0-5-answer-step250` | `trace-qwen3vl4b-alpha1-answer-step250` |",
        "|---|---:|---:|---:|---:|",
    ]
    for benchmark in sorted(comparison, key=lambda name: (benchmark_order.get(name, len(benchmark_order)), name)):
        values = []
        for model in MODEL_COLUMNS:
            score = comparison[benchmark].get(model)
            values.append("" if score is None else f"{score:.2f}")
        lines.append(f"| {benchmark} | " + " | ".join(values) + " |")

    lines.extend(
        [
            "",
            "## Detailed Results",
            "",
        "| Model | Benchmark | Split / Variant | Rows | Score | Status | Artifacts |",
        "|---|---|---|---:|---:|---|---|",
        ]
    )
    for row in rows:
        score = "" if row["score"] is None else f"{row['score']:.2f}"
        n_rows = "" if row["rows"] is None else str(row["rows"])
        rel = row["path"].parent
        try:
            rel = rel.relative_to(REPO_ROOT)
        except ValueError:
            pass
        lines.append(
            f"| `{row['model']}` | {row['benchmark']} | `{row['run']}` | {n_rows} | {score} | done | `{rel}/` |"
        )
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- ChartMuseum scores use a local `Qwen/Qwen3-32B` judge approximation because the official benchmark uses GPT-4.1-mini judging.",
            "- CharXiv, MathVision, MathVista, MathVerse, and LogicVista use local `Qwen/Qwen3-32B` judging where required by the evaluator.",
            "- ScreenSpotPro is reported as a pooled sample-wise aggregate over the six `ScreenSpot_Pro_*` subsets when all subset scores are present.",
            "- If an evaluator emits category scores without an explicit overall score, the table reports the mean over numeric category scores.",
            "- Existing per-run README files and `scores.json` files remain the source of detailed generation and judge settings.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark-root", type=Path, default=DEFAULT_BENCHMARK_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_BENCHMARK_ROOT / "results.md")
    args = parser.parse_args()
    text = build_markdown(args.benchmark_root)
    args.output.write_text(text, encoding="utf-8")
    print(f"[wrote] {args.output}")


if __name__ == "__main__":
    main()
