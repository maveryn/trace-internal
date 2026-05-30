"""Regression tests for shared task-review calibration helpers."""

from __future__ import annotations

import json
from pathlib import Path

from trace.core.task_review_calibration import load_scene_model_stats_rows, status_reasons_from_stats


def _accepted_stats() -> dict[str, object]:
    return {
        "overall": {
            "hard_frac": 0.20,
            "easy_frac": 0.20,
            "band_frac": 0.60,
            "mean_solve_rate": 0.40,
            "rollout_count": 24,
            "prompt_count": 100,
        },
        "prompt_token_stats": {"max": 512, "over_limit_count": 0},
        "response_token_stats": {"cap_rate": 0.0},
    }


def test_status_reasons_from_stats_blocks_prompt_over_limit() -> None:
    stats = _accepted_stats()
    stats["prompt_token_stats"] = {"max": 9999, "over_limit_count": 1}

    status, reasons = status_reasons_from_stats(stats, model_slug="qwen25vl7b")

    assert status == "blocked"
    assert reasons == ["prompt_over_limit"]


def test_load_scene_model_stats_rows_reads_review_status(tmp_path: Path) -> None:
    out_root = tmp_path / "review" / "task-reviews"
    out_root.mkdir(parents=True)
    task_id = "task_dummy__scene__foo"
    status_path = out_root.parent / "calibration_sweep_status.json"
    status_path.write_text(
        json.dumps(
            {
                "config": {"calibration_baseline": "v0"},
                "tasks": {
                    task_id: {
                        "domain": "dummy",
                        "scene_id": "scene",
                        "status": "accepted",
                        "models": {
                            "qwen25vl7b": {
                                "model_id": "Qwen/Qwen2.5-VL-7B-Instruct",
                                "status": "accepted",
                                "reasons": [],
                                "stats": _accepted_stats(),
                                "max_response_length": 256,
                                "solve_workbook": "solve.xlsx",
                                "calibration_stats": "stats.json",
                                "output_dir": "runs/example",
                            }
                        },
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    rows = load_scene_model_stats_rows(
        out_root=out_root,
        domain="dummy",
        scene_id="scene",
        task_ids=[task_id],
        probe_root=tmp_path / "missing-probes",
    )

    assert len(rows) == 1
    assert rows[0]["task"] == task_id
    assert rows[0]["combined_status"] == "accepted"
    assert rows[0]["model_status"] == "accepted"
    assert rows[0]["mean_solve_rate"] == 0.40
    assert rows[0]["solve_workbook"] == "solve.xlsx"


def test_load_scene_model_stats_rows_uses_latest_probe_fallback(tmp_path: Path) -> None:
    out_root = tmp_path / "review" / "task-reviews"
    out_root.mkdir(parents=True)
    probe_root = tmp_path / "probes"
    task_id = "task_dummy__scene__foo"
    old_stats = probe_root / "qwen25vl7b" / "dummy" / "scene" / task_id / "100x10_seed1" / "calibration_stats.json"
    latest_stats = probe_root / "qwen25vl7b" / "dummy" / "scene" / task_id / "100x24_seed2" / "calibration_stats.json"
    for stats_path, mean in ((old_stats, 0.30), (latest_stats, 0.55)):
        stats = _accepted_stats()
        stats["overall"] = dict(stats["overall"], mean_solve_rate=mean)
        stats["config"] = {
            "calibration_baseline": "v0",
            "max_response_length": 512,
            "probe_output_dir": str(stats_path.parent),
        }
        stats["artifacts"] = {
            "solve_workbook": "solve.xlsx",
            "calibration_stats": str(stats_path),
        }
        stats_path.parent.mkdir(parents=True, exist_ok=True)
        stats_path.write_text(json.dumps(stats), encoding="utf-8")

    rows = load_scene_model_stats_rows(
        out_root=out_root,
        domain="dummy",
        scene_id="scene",
        task_ids=[task_id],
        probe_root=probe_root,
    )

    assert len(rows) == 1
    assert rows[0]["combined_status"] == "accepted"
    assert rows[0]["model_status"] == "accepted"
    assert rows[0]["mean_solve_rate"] == 0.55
    assert rows[0]["calibration_stats"] == str(latest_stats)
