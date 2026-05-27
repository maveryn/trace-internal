"""Tests for task-complexity correlation audit helpers."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


_SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "analyze_task_complexity_correlation.py"
_SPEC = importlib.util.spec_from_file_location("analyze_task_complexity_correlation", _SCRIPT_PATH)
assert _SPEC is not None and _SPEC.loader is not None
analysis = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = analysis
_SPEC.loader.exec_module(analysis)


def test_spearman_tracks_complexity_against_inverse_solve_rate() -> None:
    complexity = [0.10, 0.40, 0.80]
    solve_rate = [0.90, 0.60, 0.20]
    difficulty = [1.0 - value for value in solve_rate]

    assert analysis.spearman(complexity, difficulty) == pytest.approx(1.0)
    assert analysis.spearman(complexity, solve_rate) == pytest.approx(-1.0)


def test_weighted_score_normalizes_weights_and_clamps_components() -> None:
    score = analysis.weighted_score(
        {"visual_scan": 1.0, "reasoning_load": 3.0},
        {"visual_scan": -1.0, "reasoning_load": 2.0},
    )

    assert score == pytest.approx(0.75)


def test_render_report_marks_target_status() -> None:
    report = analysis.render_report(
        [
            {
                "task_id": "task_target_met",
                "mode": "replay",
                "stored_rho": 0.50,
                "current_rho": 0.76,
                "mean_solve_rate": 0.42,
                "answer_mismatches": 0,
            },
            {
                "task_id": "task_below_target",
                "mode": "trace_formula",
                "stored_rho": 0.50,
                "current_rho": 0.60,
                "mean_solve_rate": 0.55,
                "answer_mismatches": 0,
            },
        ],
        target=0.75,
    )

    assert "- tasks at target: `1/2`" in report
    assert "Future revisit note:" in report
    assert "below `0.05`, drop that axis" in report
    assert "| `task_target_met` | replay | 0.500 | 0.760 | 0.260 | 0.420 | 0 | target_met |" in report
    assert (
        "| `task_below_target` | trace_formula | 0.500 | 0.600 | 0.100 | 0.550 | 0 | "
        "best_semantic_so_far |"
    ) in report
