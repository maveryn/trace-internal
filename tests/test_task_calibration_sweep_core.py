"""Tests for the shared task calibration sweep implementation."""

from __future__ import annotations

from scripts import run_task_calibration_sweep as cli_sweep
from trace.core import task_calibration_sweep as sweep


def test_cli_wrapper_reexports_core_helpers() -> None:
    assert cli_sweep.main is sweep.main
    assert cli_sweep._easy_threshold_for_rollouts is sweep._easy_threshold_for_rollouts


def test_task_calibration_sweep_repo_root_points_to_repo() -> None:
    assert (sweep.REPO_ROOT / "pyproject.toml").exists()
    assert (sweep.REPO_ROOT / "scripts" / "run_task_calibration_sweep.py").exists()


def test_easy_threshold_for_rollouts_is_strictly_over_75_percent() -> None:
    assert sweep._easy_threshold_for_rollouts(4) == 4
    assert sweep._easy_threshold_for_rollouts(24) == 19


def test_parse_models_resolves_known_alias() -> None:
    specs = sweep._parse_models("qwen25vl7b")

    assert [spec.slug for spec in specs] == ["qwen25vl7b"]
    assert specs[0].model_id == "Qwen/Qwen2.5-VL-7B-Instruct"
