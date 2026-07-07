"""Tests for the shared task calibration sweep implementation."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from scripts import run_task_calibration_sweep as cli_sweep
from trace.core import task_calibration_sweep as sweep


def test_cli_wrapper_reexports_core_helpers() -> None:
    assert cli_sweep.main is sweep.main
    assert cli_sweep._easy_threshold_for_rollouts is sweep._easy_threshold_for_rollouts


def test_task_calibration_sweep_repo_root_points_to_repo() -> None:
    assert (sweep.REPO_ROOT / "pyproject.toml").exists()
    assert (sweep.REPO_ROOT / "scripts" / "run_task_calibration_sweep.py").exists()


def test_easy_threshold_for_rollouts_is_perfect_solve_tail() -> None:
    assert sweep._easy_threshold_for_rollouts(4) == 4
    assert sweep._easy_threshold_for_rollouts(8) == 8
    assert sweep._easy_threshold_for_rollouts(24) == 24


def test_parse_models_resolves_known_alias() -> None:
    specs = sweep._parse_models("qwen25vl7b")

    assert [spec.slug for spec in specs] == ["qwen25vl7b"]
    assert specs[0].model_id == "Qwen/Qwen2.5-VL-7B-Instruct"


def _minimal_sweep_args(tmp_path: Path) -> SimpleNamespace:
    return SimpleNamespace(
        calibration_baseline="v0",
        dry_run=False,
        force=False,
        force_build=False,
        output_root=str(tmp_path / "out"),
        parquet_cpu_count=0,
        sample_count=50,
        seed=123,
        workers=0,
    )


def test_build_sample_reuses_only_matching_source_fingerprint(tmp_path: Path, monkeypatch) -> None:
    args = _minimal_sweep_args(tmp_path)
    task_id = "task_geometry__angle_relations__algebraic_angle_value"
    task_root = tmp_path / "task"
    dataset_name = "sample"
    parquet = task_root / "sample.parquet"
    dataset_root = task_root / "datasets" / "current"
    manifest = parquet.with_suffix(parquet.suffix + ".manifest.json")
    current_fingerprint = {"version": "v1", "digest": "current", "file_count": 1, "roots": ["trace/tasks"]}
    parquet.parent.mkdir(parents=True)
    parquet.write_bytes(b"parquet")
    manifest.write_text(
        json.dumps(
            {
                "calibration_baseline": "v0",
                "trace_dataset_root": str(dataset_root),
                "calibration_source_fingerprint": current_fingerprint,
            }
        )
    )

    calls: list[list[str]] = []

    monkeypatch.setattr(
        sweep,
        "_dataset_paths",
        lambda *a, **k: (task_root, dataset_name, parquet, dataset_root),
    )
    monkeypatch.setattr(sweep, "_calibration_source_fingerprint", lambda _task_id: current_fingerprint)
    monkeypatch.setattr(sweep, "_run_command", lambda cmd, **_kwargs: calls.append(cmd))

    reused_parquet, reused_dataset_root = sweep._build_sample(args, task_id, code_revision="abc")

    assert reused_parquet == parquet
    assert reused_dataset_root == dataset_root
    assert calls == []


def test_build_sample_rebuilds_stale_source_fingerprint(tmp_path: Path, monkeypatch) -> None:
    args = _minimal_sweep_args(tmp_path)
    task_id = "task_geometry__angle_relations__algebraic_angle_value"
    task_root = tmp_path / "task"
    dataset_name = "sample"
    parquet = task_root / "sample.parquet"
    dataset_root = task_root / "datasets" / "current"
    manifest = parquet.with_suffix(parquet.suffix + ".manifest.json")
    current_fingerprint = {"version": "v1", "digest": "current", "file_count": 1, "roots": ["trace/tasks"]}
    stale_fingerprint = {"version": "v1", "digest": "stale", "file_count": 1, "roots": ["trace/tasks"]}
    parquet.parent.mkdir(parents=True)
    parquet.write_bytes(b"old parquet")
    manifest.write_text(
        json.dumps(
            {
                "calibration_baseline": "v0",
                "trace_dataset_root": str(dataset_root),
                "calibration_source_fingerprint": stale_fingerprint,
            }
        )
    )

    calls: list[list[str]] = []

    def fake_run_command(cmd: list[str], **_kwargs) -> None:
        calls.append(cmd)
        parquet.write_bytes(b"new parquet")
        manifest.write_text(json.dumps({"calibration_baseline": "v0", "trace_dataset_root": str(dataset_root)}))

    monkeypatch.setattr(
        sweep,
        "_dataset_paths",
        lambda *a, **k: (task_root, dataset_name, parquet, dataset_root),
    )
    monkeypatch.setattr(sweep, "_calibration_source_fingerprint", lambda _task_id: current_fingerprint)
    monkeypatch.setattr(sweep, "_run_command", fake_run_command)

    rebuilt_parquet, rebuilt_dataset_root = sweep._build_sample(args, task_id, code_revision="abc")

    assert rebuilt_parquet == parquet
    assert rebuilt_dataset_root == dataset_root
    assert len(calls) == 1
    assert "--reset" in calls[0]
    payload = json.loads(manifest.read_text())
    assert payload["calibration_source_fingerprint"] == current_fingerprint


def test_stats_must_match_parquet_source_fingerprint(tmp_path: Path) -> None:
    parquet = tmp_path / "sample.parquet"
    stats_path = tmp_path / "calibration_stats.json"
    fingerprint = {"version": "v1", "digest": "current", "file_count": 1, "roots": ["trace/tasks"]}
    parquet.write_bytes(b"parquet")
    parquet.with_suffix(parquet.suffix + ".manifest.json").write_text(
        json.dumps(
            {
                "calibration_baseline": "v0",
                "trace_dataset_root": str(tmp_path / "dataset"),
                "calibration_source_fingerprint": fingerprint,
            }
        )
    )

    stats_path.write_text(
        json.dumps(
            {
                "config": {
                    "calibration_baseline": "v0",
                    "parquet": str(parquet),
                    "calibration_source_fingerprint": {
                        "version": "v1",
                        "digest": "stale",
                        "file_count": 1,
                        "roots": ["trace/tasks"],
                    },
                }
            }
        )
    )
    assert not sweep._stats_match_parquet(stats_path, parquet, "v0")

    stats_path.write_text(
        json.dumps(
            {
                "config": {
                    "calibration_baseline": "v0",
                    "parquet": str(parquet),
                    "calibration_source_fingerprint": fingerprint,
                }
            }
        )
    )
    assert sweep._stats_match_parquet(stats_path, parquet, "v0")


def test_model_status_uses_current_strict_target_gates() -> None:
    boundary_stats = {
        "overall": {
            "hard_frac": 0.50,
            "easy_frac": 0.25,
            "mean_solve_rate": 0.10,
        },
        "prompt_token_stats": {"over_limit_count": 0},
        "response_token_stats": {"cap_rate": 0.25},
    }

    assert sweep._model_status(boundary_stats, cap_threshold=0.25) == ("accepted", [])

    low_mean_stats = {
        "overall": {
            "hard_frac": 0.0,
            "easy_frac": 0.0,
            "mean_solve_rate": 0.09,
        },
        "prompt_token_stats": {"over_limit_count": 0},
        "response_token_stats": {"cap_rate": 0.0},
    }

    assert sweep._model_status(low_mean_stats, cap_threshold=0.25) == (
        "needs_manual_tuning",
        ["mean_solve_rate"],
    )
