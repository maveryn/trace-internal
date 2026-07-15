#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from benchmark_queue_lib import (  # noqa: E402
    TRACE_FINAL25_BENCHMARK_CATEGORIES,
    extract_score_and_rows,
    score_path,
    spec_by_key,
)


def _parse_model_entry(value: str) -> tuple[str, str]:
    slug, separator, label = value.partition("=")
    if not separator or not slug.strip() or not label.strip():
        raise argparse.ArgumentTypeError("Expected MODEL_SLUG=DISPLAY_LABEL")
    return slug.strip(), label.strip()


def _write_excel(path: Path, sheets: dict[str, pd.DataFrame]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for name, frame in sheets.items():
            frame.to_excel(writer, sheet_name=name, index=False)


def _fmt(value: float) -> str:
    return f"{value:.2f}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize a strict three-seed TRACE Final25 campaign.")
    parser.add_argument("--score-root-base", type=Path, required=True)
    parser.add_argument("--model-entry", action="append", type=_parse_model_entry, required=True)
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 43, 44])
    parser.add_argument("--excel", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    parser.add_argument("--title", default="TRACE Final25 Temp0.6 Three-Seed Results")
    args = parser.parse_args()

    model_entries = list(dict(args.model_entry).items())
    benchmark_rows: list[tuple[str, str]] = [
        (category, key)
        for category, keys in TRACE_FINAL25_BENCHMARK_CATEGORIES.items()
        for key in keys
    ]
    seed_records: list[dict[str, Any]] = []
    missing: list[str] = []
    for seed in args.seeds:
        benchmark_root = args.score_root_base / f"seed_{seed}" / "benchmark"
        for category, benchmark_key in benchmark_rows:
            spec = spec_by_key(benchmark_key)
            for model_slug, model_label in model_entries:
                path = score_path(spec, model_slug, benchmark_root)
                if not path.exists():
                    missing.append(str(path))
                    continue
                payload = json.loads(path.read_text(encoding="utf-8"))
                score, rows = extract_score_and_rows(payload)
                if score is None or not math.isfinite(float(score)):
                    raise ValueError(f"Missing finite primary score in {path}")
                seed_records.append(
                    {
                        "category": category,
                        "benchmark_key": benchmark_key,
                        "benchmark": spec.display,
                        "model_slug": model_slug,
                        "model": model_label,
                        "seed": seed,
                        "rows": rows or payload.get("rows"),
                        "score": float(score),
                        "score_path": str(path),
                    }
                )
    if missing:
        preview = "\n".join(missing[:20])
        raise FileNotFoundError(f"Missing {len(missing)} Final25 score files; first paths:\n{preview}")

    seed_values = pd.DataFrame(seed_records)
    summary_rows: list[dict[str, Any]] = []
    for category, benchmark_key in benchmark_rows:
        spec = spec_by_key(benchmark_key)
        row: dict[str, Any] = {
            "Category": category,
            "Benchmark": spec.display,
            "Rows": int(seed_values[seed_values["benchmark_key"] == benchmark_key]["rows"].dropna().max()),
        }
        for model_slug, model_label in model_entries:
            values = seed_values[
                (seed_values["benchmark_key"] == benchmark_key)
                & (seed_values["model_slug"] == model_slug)
            ].sort_values("seed")["score"].tolist()
            if len(values) != len(args.seeds):
                raise ValueError(f"Expected {len(args.seeds)} scores for {benchmark_key}/{model_slug}, found {len(values)}")
            row[f"{model_label} mean"] = statistics.fmean(values)
            row[f"{model_label} std"] = statistics.stdev(values) if len(values) > 1 else 0.0
        summary_rows.append(row)

    summary = pd.DataFrame(summary_rows)
    average: dict[str, Any] = {"Category": "Overall", "Benchmark": "Average", "Rows": None}
    for model_slug, model_label in model_entries:
        per_seed = (
            seed_values[seed_values["model_slug"] == model_slug]
            .groupby("seed", sort=True)["score"]
            .mean()
            .tolist()
        )
        average[f"{model_label} mean"] = statistics.fmean(per_seed)
        average[f"{model_label} std"] = statistics.stdev(per_seed) if len(per_seed) > 1 else 0.0
    summary = pd.concat([summary, pd.DataFrame([average])], ignore_index=True)

    metadata = pd.DataFrame(
        [
            {"key": "suite", "value": "trace_final25"},
            {"key": "seeds", "value": ",".join(map(str, args.seeds))},
            {"key": "decoding", "value": "temperature=0.6, top_p=1, top_k=-1, no penalties, max_tokens=4096"},
            {"key": "judge", "value": "Qwen/Qwen3-32B, temperature=0"},
            {"key": "score_root_base", "value": str(args.score_root_base)},
        ]
        + [
            {"key": f"model/{slug}", "value": label}
            for slug, label in model_entries
        ]
    )
    categories = pd.DataFrame(
        [
            {"Category": category, "Benchmarks": ", ".join(spec_by_key(key).display for key in keys), "Count": len(keys)}
            for category, keys in TRACE_FINAL25_BENCHMARK_CATEGORIES.items()
        ]
    )
    _write_excel(
        args.excel,
        {
            "mean_std": summary,
            "seed_values": seed_values,
            "categories": categories,
            "metadata": metadata,
        },
    )

    lines = [f"# {args.title}", "", f"Seeds: `{', '.join(map(str, args.seeds))}`", ""]
    headers = ["Category", "Benchmark", "Rows"] + [label for _, label in model_entries]
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("|" + "|".join(["---"] * len(headers)) + "|")
    for _, row in summary.iterrows():
        values = [str(row["Category"]), str(row["Benchmark"]), "" if pd.isna(row["Rows"]) else str(int(row["Rows"]))]
        for _, label in model_entries:
            values.append(f"{_fmt(float(row[f'{label} mean']))} +/- {_fmt(float(row[f'{label} std']))}")
        lines.append("| " + " | ".join(values) + " |")
    lines.extend(
        [
            "",
            "Decoding: temperature 0.6, top-p 1, top-k -1, no penalties, maximum 4096 generated tokens.",
            "Judge: Qwen3-32B at temperature 0 through the frozen Final25 scoring contracts.",
        ]
    )
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[final25-summary:done] rows={len(summary_rows)} models={len(model_entries)} excel={args.excel} markdown={args.markdown}")


if __name__ == "__main__":
    main()
