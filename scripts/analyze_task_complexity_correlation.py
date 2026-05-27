#!/usr/bin/env python
"""Audit TRACE task-complexity correlation against explicit solve artifacts.

The script never runs model inference. It joins caller-provided solve-rate
artifacts with the corresponding TRACE train/traces records and reports
Spearman(complexity_score, 1 - solve_rate).

The previous hardcoded pilot artifacts were intentionally removed: current
calibration uses fresh, baseline-tagged artifacts from
``scripts/run_task_calibration_sweep.py`` instead of legacy ``probe_100_v*``
paths.
"""

from __future__ import annotations

import argparse
import io
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Mapping, Sequence

import pandas as pd
import zstandard as zstd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import trace.tasks  # noqa: F401  # Registers tasks for replay mode.
from trace.core.task_group_config import get_task_group_defaults, resolve_task_group_section_defaults
from trace.tasks.registry import create_task


@dataclass(frozen=True)
class PilotTaskSpec:
    task_id: str
    domain: str
    task_group: str
    parquet_path: Path
    solve_path: Path
    mode: str


PILOT_TASKS: tuple[PilotTaskSpec, ...] = ()


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def normalize(value: float, lower: float, upper: float) -> float:
    if float(upper) <= float(lower):
        return 0.0
    return clamp01((float(value) - float(lower)) / (float(upper) - float(lower)))


def spearman(x: Sequence[float], y: Sequence[float]) -> float:
    x_series = pd.Series(x, dtype="float64")
    y_series = pd.Series(y, dtype="float64")
    if x_series.nunique(dropna=True) < 2 or y_series.nunique(dropna=True) < 2:
        return float("nan")
    return float(x_series.rank(method="average").corr(y_series.rank(method="average")))


def current_weights(spec: PilotTaskSpec) -> Dict[str, float]:
    cfg = get_task_group_defaults(spec.domain, spec.task_group)
    defaults = resolve_task_group_section_defaults(cfg, "complexity", task_id=spec.task_id)
    weights = defaults.get("criteria_weights", {})
    if not isinstance(weights, Mapping):
        raise ValueError(f"missing complexity.criteria_weights for {spec.task_id}")
    return {str(key): float(value) for key, value in weights.items() if float(value) > 0.0}


def weighted_score(weights: Mapping[str, float], components: Mapping[str, float]) -> float:
    missing = [key for key in weights if key not in components]
    if missing:
        raise ValueError(f"missing complexity components: {missing}")
    total = sum(float(value) for value in weights.values())
    if total <= 0.0:
        raise ValueError("complexity weights must sum to a positive value")
    return clamp01(sum(float(weights[key]) * clamp01(float(components[key])) for key in weights) / total)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _dataset_root(parquet_path: Path) -> Path:
    manifest_path = Path(str(parquet_path) + ".manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return Path(str(manifest["trace_dataset_root"]))


def load_trace_records(dataset_root: Path) -> list[dict[str, Any]]:
    shard_path = dataset_root / "traces" / "trace_shard_0001.jsonl.zst"
    with shard_path.open("rb") as raw:
        text = io.TextIOWrapper(zstd.ZstdDecompressor().stream_reader(raw), encoding="utf-8")
        return [json.loads(line) for line in text if line.strip()]


def load_joined_artifact(spec: PilotTaskSpec) -> pd.DataFrame:
    dataset_root = _dataset_root(spec.parquet_path)
    train_rows = _read_jsonl(dataset_root / "train_instances.jsonl")
    trace_rows = load_trace_records(dataset_root)
    if len(train_rows) != len(trace_rows):
        raise ValueError(f"{spec.task_id}: train/trace row count mismatch")
    records: list[dict[str, Any]] = []
    for train, trace in zip(train_rows, trace_rows):
        complexity = train.get("task_complexity") or {}
        records.append(
            {
                "uid": str(train["instance_id"]),
                "instance_seed": int(train["instance_seed"]),
                "answer_gt": train.get("answer_gt"),
                "stored_score": float(complexity.get("complexity_score", 0.0)),
                "stored_components": dict(complexity.get("complexity_components") or {}),
                "query_params": dict((trace.get("query_spec") or {}).get("params") or {}),
                "execution_trace": dict(trace.get("execution_trace") or {}),
            }
        )
    solve = pd.DataFrame(_read_jsonl(spec.solve_path))[["uid", "solve_rate"]]
    return solve.merge(pd.DataFrame(records), on="uid", how="inner")


def replay_scores(spec: PilotTaskSpec, rows: pd.DataFrame) -> tuple[list[float], int]:
    task = create_task(spec.task_id)
    scores: list[float] = []
    mismatches = 0
    for row in rows.itertuples(index=False):
        output = task.generate(
            int(row.instance_seed),
            params=dict(row.query_params),
            max_attempts=250,
        )
        if output.answer_gt.to_dict() != row.answer_gt:
            mismatches += 1
        scores.append(float(output.complexity.complexity_score))
    return scores, mismatches


def _chart_extremum_components(execution: Mapping[str, Any]) -> Dict[str, float]:
    variant_load = {
        "ranked_largest_series_share": 0.00,
        "ranked_largest_pair_ratio": 0.03,
        "ranked_smallest_pair_ratio": 0.25,
        "ranked_largest_increase": 0.29,
        "ranked_smallest_series_share": 0.42,
        "ranked_largest_gap": 0.69,
        "ranked_largest_decrease": 1.00,
        "ranked_smallest_gap": 1.00,
    }[str(execution["query_id"])]
    rank_range = [1, 3]
    category_norm = normalize(int(execution["category_count"]), 5, 15)
    series_norm = normalize(int(execution["series_count"]), 3, 4)
    return {
        "visual_scan": clamp01((0.70 * category_norm) + (0.30 * series_norm)),
        "reasoning_load": clamp01(0.85 * variant_load + 0.15 * normalize(int(execution["answer_rank"]), *rank_range)),
        "scene_variant_load": {
            "grouped_bar": 0.0,
            "grouped_horizontal_bar": 0.50,
            "grouped_lollipop": 0.55,
            "multi_line": 1.0,
        }[str(execution["scene_variant"])],
    }


def _tile_reachability_components(execution: Mapping[str, Any]) -> Dict[str, float]:
    rows = int(execution["rows"])
    cols = int(execution["cols"])
    board_cell_count = rows * cols
    min_board = 3 * 3
    max_board = 7 * 7
    obstacle_fraction = float(execution["obstacle_fraction"])
    reachable_fraction = float(execution["reachable_fraction"])
    return {
        "visual_scan": clamp01(
            0.80 * normalize(board_cell_count, min_board, max_board)
            + 0.20 * normalize(obstacle_fraction, 0.16, 0.36)
        ),
        "reasoning_load": clamp01(
            0.45 * normalize(board_cell_count, min_board, max_board)
            + 0.30 * normalize(int(execution["answer_value"]), int(execution["answer_min"]), int(execution["answer_max"]))
            + 0.10 * normalize(cols, 3, 7)
            + 0.10 * normalize(1.0 - obstacle_fraction, 1.0 - 0.36, 1.0 - 0.16)
            + 0.05 * normalize(1.0 - reachable_fraction, 1.0 - 0.75, 1.0 - 0.12)
        ),
    }


def _puzzle_logic_components(execution: Mapping[str, Any]) -> Dict[str, float]:
    variant_load = {
        "row_uniqueness": 0.00,
        "row_and_column_uniqueness": 0.50,
        "column_uniqueness": 1.00,
    }[str(execution["query_id"])]
    board_size_norm = normalize(int(execution["board_size"]), *list(execution["board_size_range"]))
    return {
        "visual_scan": normalize(int(execution["cell_count"]), *list(execution["cell_count_range"])),
        "reasoning_load": clamp01((0.75 * variant_load) + (0.25 * board_size_norm)),
        "scene_variant_load": {"logic_strip": 0.16, "logic_card": 0.24, "logic_outline": 0.20}[str(execution["scene_variant"])],
    }


def _clock_components(execution: Mapping[str, Any]) -> Dict[str, float]:
    variant = str(execution["query_id"])
    time_base = {
        "minutes_before": 0.00,
        "minutes_after": 0.05,
        "seconds_after": 0.35,
        "seconds_before": 1.00,
    }[variant]
    is_seconds = variant in {"seconds_after", "seconds_before"}
    minute_complexity = 0.25 if int(execution["shown_minute"]) in {0, 15, 30, 45} else 0.55
    second_complexity = 0.20 if int(execution["shown_second"]) in {0, 15, 30, 45} else 0.55
    offset_norm = (
        normalize(int(execution.get("delta_seconds") or 0), 5, 36000)
        if is_seconds
        else normalize(int(execution.get("delta_minutes") or 0), 5, 600)
    )
    minute_norm = normalize(int(execution["shown_minute"]), 0, 55)
    second_norm = normalize(int(execution["shown_second"]), 0, 55)
    return {
        "time_reading": clamp01(
            (0.55 * time_base)
            + (0.35 * minute_norm)
            + (0.10 * offset_norm)
        ),
        "visual_scan": clamp01(
            {"classic": 0.34, "minimal": 0.22, "outline": 0.26}[str(execution["scene_variant"])]
            + {"studio": 0.00, "accented": 0.04, "marker": 0.06}[str(execution["style_variant"])]
            + (0.10 * minute_norm)
            + (0.08 if is_seconds else 0.0)
        ),
        "ambiguity": clamp01(
            (0.45 * (1.0 - normalize(float(execution["min_hand_angle_gap_deg"]), 20.0, 180.0)))
            + (0.22 * minute_complexity)
            + (0.23 * second_complexity if is_seconds else 0.0)
            + (0.12 * second_norm if is_seconds else 0.0)
            + 0.14
        ),
        "clutter": clamp01(
            {"classic": 0.32, "minimal": 0.12, "outline": 0.18}[str(execution["scene_variant"])]
            + {"studio": 0.00, "accented": 0.05, "marker": 0.08}[str(execution["style_variant"])]
        ),
    }


def _paired_forms_components(execution: Mapping[str, Any]) -> Dict[str, float]:
    variant_load = {
        "sum_absolute_quantity_differences": 0.00,
        "total_amount_delta": 0.50,
        "shortfall_minus_overage_value": 1.00,
    }[str(execution["query_id"])]
    item_count = int(execution["item_count"])
    evidence_count = len(execution["evidence_bbox_ids"])
    mismatch_count = len(execution["mismatch_item_ids"])
    return {
        "visual_scan": normalize(item_count, *list(execution["item_count_range"])),
        "reasoning_load": clamp01(
            (0.60 * variant_load)
            + (0.25 * normalize(evidence_count, 4, 60))
            + (0.15 * normalize(mismatch_count, 4, item_count))
        ),
        "scene_variant_load": {"purchase_receipt_pair": 0.34}[str(execution["scene_variant"])],
    }


TRACE_FORMULA_COMPONENTS: dict[str, Callable[[Mapping[str, Any]], Dict[str, float]]] = {
    "task_puzzles__logic_grid__grid_uniqueness_completion_label": _puzzle_logic_components,
    "task_puzzles__analog_clock__offset_readout": _clock_components,
    "task_pages__paired_forms__reconciliation_value": _paired_forms_components,
}


def trace_formula_scores(spec: PilotTaskSpec, rows: pd.DataFrame) -> list[float]:
    if spec.task_id not in TRACE_FORMULA_COMPONENTS:
        raise ValueError(f"no trace formula registered for {spec.task_id}")
    weights = current_weights(spec)
    component_builder = TRACE_FORMULA_COMPONENTS[spec.task_id]
    return [weighted_score(weights, component_builder(dict(row.execution_trace))) for row in rows.itertuples(index=False)]


def analyze_task(spec: PilotTaskSpec) -> dict[str, Any]:
    rows = load_joined_artifact(spec)
    if spec.mode == "replay":
        current_scores, mismatches = replay_scores(spec, rows)
        score_source = "replay"
    elif spec.mode == "trace_formula":
        current_scores = trace_formula_scores(spec, rows)
        mismatches = 0
        score_source = "trace_formula"
    else:
        raise ValueError(f"unsupported mode: {spec.mode}")
    difficulty = [1.0 - float(value) for value in rows["solve_rate"].tolist()]
    stored_scores = [float(value) for value in rows["stored_score"].tolist()]
    return {
        "task_id": spec.task_id,
        "mode": score_source,
        "n": int(len(rows)),
        "mean_solve_rate": float(rows["solve_rate"].mean()),
        "stored_rho": spearman(stored_scores, difficulty),
        "current_rho": spearman(current_scores, difficulty),
        "answer_mismatches": int(mismatches),
        "unique_current_scores": int(pd.Series(current_scores).nunique(dropna=True)),
    }


def _format_float(value: float) -> str:
    if value is None or math.isnan(float(value)):
        return "n/a"
    return f"{float(value):.3f}"


def render_report(results: Sequence[Mapping[str, Any]], *, target: float) -> str:
    reached = sum(1 for row in results if not math.isnan(float(row["current_rho"])) and float(row["current_rho"]) >= target)
    lines = [
        "# Task Complexity Correlation Pilot",
        "",
        "Metric: `Spearman(complexity_score, 1 - solve_rate)` on retained 100x64 solve artifacts.",
        "No model inference or solve-rate regeneration is performed.",
        "",
        f"- target: `{target:.2f}`",
        f"- tasks at target: `{reached}/{len(results)}`",
        "",
        "| Task | Score source | Stored rho | Current rho | Delta | Mean solve | Mismatches | Status |",
        "|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in sorted(results, key=lambda item: str(item["task_id"])):
        stored = float(row["stored_rho"])
        current = float(row["current_rho"])
        status = "target_met" if not math.isnan(current) and current >= target else "best_semantic_so_far"
        lines.append(
            f"| `{row['task_id']}` | {row['mode']} | {_format_float(stored)} | {_format_float(current)} | "
            f"{_format_float(current - stored)} | {_format_float(float(row['mean_solve_rate']))} | "
            f"{int(row['answer_mismatches'])} | {status} |"
        )
    lines.append("")
    lines.append(
        "Trace-formula rows are used only where saved params do not exactly replay the retained sample; formulas mirror the current task complexity code."
    )
    lines.extend(
        [
            "",
            "Future revisit note: this pilot is intentionally not final. Revisit the below-target tasks after broader task calibration, because some tasks may need distribution or variant changes rather than further complexity-score tuning.",
            "",
            "Axis pruning policy: if a task/domain complexity axis needs a configured weight below `0.05`, drop that axis from the task/domain complexity definition instead of keeping a near-zero weighted component.",
        ]
    )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("plans/task_complexity_correlation_audit.md"))
    parser.add_argument("--target", type=float, default=0.75)
    parser.add_argument("--task", action="append", default=[], help="Optional task id filter; repeatable.")
    parser.add_argument("--no-write", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    selected = set(str(task_id) for task_id in args.task)
    specs = [spec for spec in PILOT_TASKS if not selected or spec.task_id in selected]
    if not specs:
        raise SystemExit(
            "no default pilot artifacts are bundled; provide current baseline artifacts "
            "before using this legacy complexity-correlation helper"
        )
    results = [analyze_task(spec) for spec in specs]
    report = render_report(results, target=float(args.target))
    print(report)
    if not bool(args.no_write):
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(report, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
