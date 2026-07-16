from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

from scripts.benchmark_queue_lib import (
    TRACE_FINAL25_BENCHMARK_CATEGORIES,
    TRACE_FINAL26_BENCHMARKS,
    TRACE_FINAL31_BENCHMARKS,
    score_path,
    spec_by_key,
)
from scripts.summarize_trace_final25_multiseed import (
    _benchmark_rows_for_suite,
    _categories_for_suite,
    _default_title,
    main,
)


def test_all26_categories_add_mmvp_without_replacing_countqa() -> None:
    frozen = _categories_for_suite("frozen")
    all26 = _categories_for_suite("all26")

    assert frozen == TRACE_FINAL25_BENCHMARK_CATEGORIES
    assert all26["Perception & Counting"] == (
        *TRACE_FINAL25_BENCHMARK_CATEGORIES["Perception & Counting"],
        "mmvp",
    )
    assert "countqa" in all26["Perception & Counting"]
    assert [key for _, key in _benchmark_rows_for_suite("all26")] == list(TRACE_FINAL26_BENCHMARKS)
    assert dict((key, category) for category, key in _benchmark_rows_for_suite("all26"))["mmvp"] == (
        "Perception & Counting"
    )
    assert _default_title("frozen", [42, 43, 44]) == "TRACE Final25 Temp0.6 Three-Seed Results"
    assert _default_title("all26", [42]) == "TRACE All26 Temp0.6 Single-Seed Results"


def test_all26_summary_uses_suite_title_metadata_and_mmvp_score(
    tmp_path: Path,
    monkeypatch,
) -> None:
    score_root = tmp_path / "scores"
    benchmark_root = score_root / "seed_42" / "benchmark"
    for benchmark_key in TRACE_FINAL26_BENCHMARKS:
        path = score_path(spec_by_key(benchmark_key), "trace-model", benchmark_root)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"score": 50.0, "rows": 2}), encoding="utf-8")

    excel = tmp_path / "all26.xlsx"
    markdown = tmp_path / "all26.md"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "summarize_trace_final25_multiseed.py",
            "--score-root-base",
            str(score_root),
            "--model-entry",
            "trace-model=TRACE model",
            "--seeds",
            "42",
            "--suite",
            "all26",
            "--excel",
            str(excel),
            "--markdown",
            str(markdown),
        ],
    )

    main()

    sheets = pd.read_excel(excel, sheet_name=None)
    metadata = dict(zip(sheets["metadata"]["key"], sheets["metadata"]["value"]))
    perception = sheets["categories"].loc[
        sheets["categories"]["Category"] == "Perception & Counting"
    ].iloc[0]
    mmvp = sheets["mean_std"].loc[sheets["mean_std"]["Benchmark"] == "MMVP"].iloc[0]
    report = markdown.read_text(encoding="utf-8")

    assert metadata["suite"] == "trace_final26"
    assert metadata["suite_view"] == "all26"
    assert int(metadata["benchmark_count"]) == 26
    assert int(perception["Count"]) == 5
    assert "CountQA" in perception["Benchmarks"]
    assert "MMVP" in perception["Benchmarks"]
    assert mmvp["Category"] == "Perception & Counting"
    assert mmvp["TRACE model mean"] == 50.0
    assert report.startswith("# TRACE All26 Temp0.6 Single-Seed Results\n")
    assert "official VLMEvalKit MMVP paired-option evaluation" in report


def test_all31_summary_reports_categories_and_trace_deltas(tmp_path: Path, monkeypatch) -> None:
    score_root = tmp_path / "scores"
    benchmark_root = score_root / "seed_42" / "benchmark"
    values = {"base": 40.0, "trace": 50.0, "vero": 45.0}
    for benchmark_key in TRACE_FINAL31_BENCHMARKS:
        for slug, score in values.items():
            path = score_path(spec_by_key(benchmark_key), slug, benchmark_root)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"score": score, "rows": 2}), encoding="utf-8")

    excel = tmp_path / "all31.xlsx"
    markdown = tmp_path / "all31.md"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "summarize_trace_final25_multiseed.py",
            "--score-root-base", str(score_root),
            "--model-entry", "base=Base",
            "--model-entry", "trace=TRACE",
            "--model-entry", "vero=VERO",
            "--delta", "TRACE - Base=trace=base",
            "--delta", "TRACE - VERO=trace=vero",
            "--seeds", "42",
            "--suite", "all31",
            "--excel", str(excel),
            "--markdown", str(markdown),
        ],
    )

    main()

    sheets = pd.read_excel(excel, sheet_name=None)
    metadata = dict(zip(sheets["metadata"]["key"], sheets["metadata"]["value"]))
    overall = sheets["mean_std"].iloc[-1]
    assert metadata["suite"] == "trace_final31"
    assert int(metadata["benchmark_count"]) == 31
    assert int(metadata["rows_per_model_seed"]) == 62
    assert overall["TRACE - Base"] == 10.0
    assert overall["TRACE - VERO"] == 5.0
    assert len(sheets["category_summary"]) == 6
    assert "## Category Means" in markdown.read_text(encoding="utf-8")
