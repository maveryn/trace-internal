"""Regression tests for task-group default config loading."""

from __future__ import annotations

from trace.core.task_group_config import get_task_group_defaults


def test_geometry_measurement_defaults_loaded() -> None:
    cfg = get_task_group_defaults("geometry", "measurement")
    assert int(cfg["generation"]["candidate_count"]) == 7
    assert int(cfg["rendering"]["canvas_size"]) == 768
    assert float(cfg["visual"]["noise"]["apply_prob"]) == 0.75


def test_tile_path_defaults_loaded() -> None:
    cfg = get_task_group_defaults("tile", "path")
    assert int(cfg["generation"]["rows"]) == 8
    assert int(cfg["rendering"]["canvas_size"]) == 640
    assert float(cfg["visual"]["noise"]["apply_prob"]) == 0.0


def test_unknown_group_returns_empty() -> None:
    assert get_task_group_defaults("missing_domain", "missing_group") == {}
